"""Export der Datenbank in eine kompakte JSON-Datei für das Web-Dashboard.

Das Dashboard (``docs/index.html``) berechnet alle Kennzahlen im Browser aus
stündlichen Spaltenarrays. Dadurch lassen sich Filter (Jahr, Jahreszeit,
Tagtyp) frei kombinieren, ohne dass ein Server nötig ist (GitHub Pages).

Aufruf::

    python -m energy_analytics.dashboard_export
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import closing
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DATABASE_PATH, PROJECT_ROOT
from .database import load_energy_data

logger = logging.getLogger(__name__)

DASHBOARD_DATA_FILE = PROJECT_ROOT / "docs" / "data" / "dashboard.json"
FORECAST_TEST_START = "2025-01-01"
DATA_SOURCE = "Energy-Charts API (Fraunhofer ISE) · Bundesnetzagentur | SMARD.de · CC BY 4.0"


def hourly_payload(df: pd.DataFrame) -> dict:
    """Spaltenorientierte Stundenwerte (kompakt gerundet)."""
    first_day = df["date"].min()
    return {
        "day": ((df["date"] - first_day).dt.days).astype(int).tolist(),
        "h": df["hour"].astype(int).tolist(),
        "price": df["price"].round(2).tolist(),
        "wind_on": df["wind_onshore"].round().astype(int).tolist(),
        "wind_off": df["wind_offshore"].round().astype(int).tolist(),
        "solar": df["solar"].round().astype(int).tolist(),
        "load": df["load"].round().astype(int).tolist(),
    }


def write_forecast_tables(test: pd.DataFrame, preds: dict, db_path: Path) -> None:
    """Schreibt Prognosen und Kennzahlen als Tabellen in die DB (Quelle für Power BI)."""
    from .modeling import evaluate

    table = pd.DataFrame(
        {
            "timestamp": test["timestamp"].to_numpy(),
            "timestamp_local": test["timestamp_local"].to_numpy(),
            "date": test["date"].to_numpy(),
            "hour": test["hour"].to_numpy(),
            "month": test["month"].to_numpy(),
            "actual": test["price"].to_numpy(),
            "naive_24h": preds["Naiv (Vortag)"],
            "naive_168h": preds["Naiv (Vorwoche)"],
            "linear_regression": np.round(preds["Lineare Regression"], 2),
            "xgboost": np.round(preds["XGBoost"], 2),
        }
    )
    metrics = pd.DataFrame(
        [{"model": name, **evaluate(test["price"], p)} for name, p in preds.items()]
    )
    with closing(sqlite3.connect(db_path)) as conn:
        table.to_sql("forecast_predictions", conn, if_exists="replace", index=False)
        metrics.to_sql("model_metrics", conn, if_exists="replace", index=False)
        conn.commit()


def forecast_payload(
    df: pd.DataFrame, test_start: str = FORECAST_TEST_START, db_path: Path = DATABASE_PATH
) -> dict:
    """Trainiert die Modelle aus Notebook 05 und exportiert die Testjahr-Prognose."""
    from sklearn.linear_model import LinearRegression
    from xgboost import XGBRegressor

    from .modeling import MODEL_FEATURES, TARGET, add_forecast_features, evaluate, time_split

    feats = add_forecast_features(df)
    train, test = time_split(feats, test_start)
    linreg = LinearRegression().fit(train[MODEL_FEATURES], train[TARGET])
    xgb = XGBRegressor(
        n_estimators=600,
        learning_rate=0.03,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    ).fit(train[MODEL_FEATURES], train[TARGET])

    preds = {
        "Naiv (Vortag)": test["price_lag_24"].to_numpy(),
        "Naiv (Vorwoche)": test["price_lag_168"].to_numpy(),
        "Lineare Regression": linreg.predict(test[MODEL_FEATURES]),
        "XGBoost": xgb.predict(test[MODEL_FEATURES]),
    }
    write_forecast_tables(test, preds, db_path)
    start_index = int(np.flatnonzero(df["timestamp"].to_numpy() == test["timestamp"].iloc[0])[0])
    importance = pd.Series(xgb.feature_importances_, index=MODEL_FEATURES).sort_values(
        ascending=False
    )
    return {
        "start_index": start_index,
        "pred": np.round(preds["XGBoost"], 2).tolist(),
        "metrics": {
            name: {k: round(v, 2) for k, v in evaluate(test[TARGET], p).items()}
            for name, p in preds.items()
        },
        "importance": {k: round(float(v), 4) for k, v in importance.items()},
        "train_period": "2023–2024",
        "test_period": "2025",
    }


def build_payload(db_path: Path = DATABASE_PATH, with_forecast: bool = True) -> dict:
    df = load_energy_data(db_path)
    payload = {
        "meta": {
            "first_day": df["date"].min().strftime("%Y-%m-%d"),
            "last_day": df["date"].max().strftime("%Y-%m-%d"),
            "hours": len(df),
            "bidding_zone": "DE-LU",
            "source": DATA_SOURCE,
            "generated": pd.Timestamp.now(tz="Europe/Berlin").strftime("%Y-%m-%d"),
        },
        "hourly": hourly_payload(df),
    }
    if with_forecast:
        payload["forecast"] = forecast_payload(df, db_path=db_path)
    return payload


def export(path: Path = DASHBOARD_DATA_FILE, db_path: Path = DATABASE_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload(db_path)
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    logger.info("Dashboard-Daten geschrieben: %s (%.0f KB)", path, path.stat().st_size / 1024)
    return path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    export()
