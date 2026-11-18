"""Bereinigung und Harmonisierung der Rohdaten zu einer stündlichen Zeitreihe.

Wichtige fachliche Entscheidungen:

* Alle Zeitstempel werden intern in UTC geführt. So entstehen bei der
  Zeitumstellung (Sommer-/Winterzeit) weder doppelte noch fehlende Stunden.
* Seit dem 01.10.2025 werden Day-Ahead-Preise in 15-Minuten-Auflösung
  gehandelt. Erzeugung und Last liegen ebenfalls viertelstündlich vor.
  Alle Reihen werden einheitlich auf Stundenmittelwerte aggregiert.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from .config import DEFAULT_PERIOD, LOCAL_TZ, Period

logger = logging.getLogger(__name__)

ENERGY_COLUMNS = ["price", "wind_offshore", "wind_onshore", "solar", "load"]


def read_raw_csv(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def to_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregiert (Viertel-)Stundenwerte auf Stundenmittelwerte (UTC)."""
    return (
        df.assign(timestamp=df["timestamp"].dt.tz_convert("UTC"))
        .set_index("timestamp")
        .sort_index()
        .resample("1h")
        .mean()
        .reset_index()
    )


def build_hourly_dataset(
    prices: pd.DataFrame,
    power: pd.DataFrame,
    period: Period = DEFAULT_PERIOD,
    include_history: bool = True,
) -> pd.DataFrame:
    """Führt Preise und Erzeugungsdaten zu einem stündlichen Datensatz zusammen.

    Bei ``include_history=True`` bleiben die Stunden vor dem Periodenstart
    erhalten, damit daraus Lag-Features berechnet werden können.
    """
    hourly = pd.merge(to_hourly(prices), to_hourly(power), on="timestamp", how="inner")
    hourly["wind"] = hourly["wind_offshore"] + hourly["wind_onshore"]

    start = period.start_ts - pd.Timedelta(days=period.history_days if include_history else 0)
    mask = (hourly["timestamp"] >= start) & (hourly["timestamp"] < period.end_ts)
    return hourly.loc[mask].reset_index(drop=True)


@dataclass
class QualityReport:
    rows: int
    start: pd.Timestamp
    end: pd.Timestamp
    missing_hours: int
    duplicate_timestamps: int
    missing_values: dict[str, int]

    @property
    def ok(self) -> bool:
        return (
            self.missing_hours == 0
            and self.duplicate_timestamps == 0
            and not any(self.missing_values.values())
        )

    def __str__(self) -> str:
        start = self.start.tz_convert(LOCAL_TZ)
        end = self.end.tz_convert(LOCAL_TZ)
        lines = [
            f"Zeilen:              {self.rows:,}",
            f"Zeitraum (lokal):    {start:%Y-%m-%d %H:%M} bis {end:%Y-%m-%d %H:%M}",
            f"Fehlende Stunden:    {self.missing_hours}",
            f"Doppelte Zeitpunkte: {self.duplicate_timestamps}",
            f"Fehlende Werte:      {sum(self.missing_values.values())}",
            f"Status:              {'OK' if self.ok else 'PRÜFEN'}",
        ]
        return "\n".join(lines)


def quality_report(df: pd.DataFrame, columns: list[str] | None = None) -> QualityReport:
    """Prüft Vollständigkeit und Eindeutigkeit einer stündlichen Zeitreihe."""
    columns = columns or [c for c in ENERGY_COLUMNS if c in df.columns]
    ts = df["timestamp"]
    expected = pd.date_range(ts.min(), ts.max(), freq="1h")
    return QualityReport(
        rows=len(df),
        start=ts.min(),
        end=ts.max(),
        missing_hours=len(expected.difference(pd.DatetimeIndex(ts))),
        duplicate_timestamps=int(ts.duplicated().sum()),
        missing_values={c: int(df[c].isna().sum()) for c in columns},
    )
