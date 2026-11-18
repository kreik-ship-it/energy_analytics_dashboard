"""Zentrale Projektkonfiguration: Pfade, Untersuchungszeitraum, API-Parameter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DATABASE_PATH = PROJECT_ROOT / "database" / "energy_analytics.db"
SQL_DIR = PROJECT_ROOT / "sql"
FIGURES_DIR = PROJECT_ROOT / "docs" / "images"

RAW_PRICE_FILE = RAW_DIR / "price_2023_2025.csv"
RAW_POWER_FILE = RAW_DIR / "power_2023_2025.csv"
HOURLY_FILE = PROCESSED_DIR / "energy_hourly_2023_2025.csv"
FEATURES_FILE = PROCESSED_DIR / "energy_features_2023_2025.csv"

LOCAL_TZ = "Europe/Berlin"


@dataclass(frozen=True)
class Period:
    """Untersuchungszeitraum in deutscher Ortszeit (Start inklusiv, Ende exklusiv)."""

    start: str = "2023-01-01"
    end: str = "2026-01-01"
    # Zusätzliche Historie vor dem Start, damit Lag-Features (bis 168 h)
    # bereits für die erste Stunde des Zeitraums berechnet werden können.
    history_days: int = 8

    @property
    def start_ts(self) -> pd.Timestamp:
        return pd.Timestamp(self.start, tz=LOCAL_TZ)

    @property
    def end_ts(self) -> pd.Timestamp:
        return pd.Timestamp(self.end, tz=LOCAL_TZ)

    @property
    def fetch_start(self) -> str:
        return (pd.Timestamp(self.start) - pd.Timedelta(days=self.history_days)).strftime(
            "%Y-%m-%d"
        )


DEFAULT_PERIOD = Period()

# Energy-Charts API (Fraunhofer ISE), Daten: Bundesnetzagentur | SMARD.de, CC BY 4.0
API_BASE_URL = "https://api.energy-charts.info"
BIDDING_ZONE = "DE-LU"
COUNTRY = "de"

# Zuordnung der API-Erzeugungsarten zu Spaltennamen
PRODUCTION_TYPES = {
    "Wind offshore": "wind_offshore",
    "Wind onshore": "wind_onshore",
    "Solar": "solar",
    "Load": "load",
}
