"""SQLite-Datenbank im Sternschema (Faktentabelle + Datumsdimension).

Tabellen
--------
``energy_data``  Faktentabelle, eine Zeile je Stunde (Grain: Stunde, UTC-Schlüssel)
``dim_date``     Datumsdimension, eine Zeile je Kalendertag (Schlüssel: ``date``)

Zusätzlich werden die Views aus ``sql/views.sql`` angelegt. Das Power-BI-Dashboard
liest direkt aus dieser Datenbank.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

from .config import DATABASE_PATH, SQL_DIR

MONTH_NAMES_DE = [
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
]
DAY_NAMES_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def build_dim_date(start: str, end: str) -> pd.DataFrame:
    """Datumsdimension für Power BI (inkl. deutscher Monats- und Wochentagsnamen)."""
    dates = pd.date_range(start, end, freq="D")
    dim = pd.DataFrame({"date": dates})
    dim["year"] = dates.year
    dim["quarter"] = dates.quarter
    dim["month"] = dates.month
    dim["month_name"] = dates.month_name()
    dim["month_name_de"] = [MONTH_NAMES_DE[m - 1] for m in dates.month]
    dim["week"] = dates.isocalendar().week.to_numpy()
    dim["day"] = dates.day
    dim["day_of_week"] = dates.day_of_week
    dim["day_name"] = dates.day_name()
    dim["day_name_de"] = [DAY_NAMES_DE[d] for d in dates.day_of_week]
    dim["is_weekend"] = dim["day_of_week"] >= 5
    dim["year_month"] = dates.strftime("%Y-%m")
    dim["year_month_key"] = dim["year"] * 100 + dim["month"]
    return dim


def write_database(
    features: pd.DataFrame,
    db_path: Path = DATABASE_PATH,
    sql_dir: Path = SQL_DIR,
) -> Path:
    """Schreibt Fakten- und Dimensionstabelle neu und legt Indizes und Views an."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    first_year = int(features["year"].min())
    last_year = int(features["year"].max())
    dim_date = build_dim_date(f"{first_year}-01-01", f"{last_year + 1}-12-31")

    with closing(sqlite3.connect(db_path)) as conn:
        # Views zuerst entfernen, da sie von den Tabellen abhängen
        for (view,) in conn.execute("SELECT name FROM sqlite_master WHERE type='view'"):
            conn.execute(f'DROP VIEW IF EXISTS "{view}"')

        features.to_sql("energy_data", conn, if_exists="replace", index=False)
        dim_date.to_sql("dim_date", conn, if_exists="replace", index=False)

        conn.executescript(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_energy_timestamp ON energy_data(timestamp);
            CREATE INDEX IF NOT EXISTS ix_energy_date ON energy_data(date);
            CREATE INDEX IF NOT EXISTS ix_energy_year_month ON energy_data(year, month);
            CREATE UNIQUE INDEX IF NOT EXISTS ux_dim_date ON dim_date(date);
            """
        )
        views_file = Path(sql_dir) / "views.sql"
        if views_file.exists():
            conn.executescript(views_file.read_text(encoding="utf-8"))
        conn.commit()
        conn.execute("VACUUM")
    return db_path


def read_sql_file(name: str, sql_dir: Path = SQL_DIR) -> str:
    """Liest eine Abfrage aus ``sql/analysis`` (Dateiname mit oder ohne Endung)."""
    path = Path(sql_dir) / "analysis" / name
    if path.suffix != ".sql":
        path = path.with_suffix(".sql")
    return path.read_text(encoding="utf-8")


def run_query(sql: str, db_path: Path = DATABASE_PATH, params=None) -> pd.DataFrame:
    with closing(sqlite3.connect(db_path)) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def run_sql_file(name: str, db_path: Path = DATABASE_PATH, sql_dir: Path = SQL_DIR) -> pd.DataFrame:
    return run_query(read_sql_file(name, sql_dir), db_path)


def load_energy_data(db_path: Path = DATABASE_PATH) -> pd.DataFrame:
    """Lädt die Faktentabelle mit korrekt typisierten Zeitstempeln."""
    df = run_query("SELECT * FROM energy_data ORDER BY timestamp", db_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["timestamp_local"] = pd.to_datetime(df["timestamp_local"])
    df["date"] = pd.to_datetime(df["date"])
    for col in ("is_weekend", "is_negative_price"):
        df[col] = df[col].astype(bool)
    return df
