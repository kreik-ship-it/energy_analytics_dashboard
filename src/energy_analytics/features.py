"""Feature Engineering für den stündlichen Energiedatensatz.

* Kalendermerkmale werden in **deutscher Ortszeit** berechnet – ein
  Tagesprofil in UTC wäre um ein bis zwei Stunden verschoben.
* Rollierende Kennzahlen nutzen ausschließlich vergangene Werte
  (``shift(1)``), damit keine Information aus der Zukunft einfließt.
"""

from __future__ import annotations

import pandas as pd

from .config import DEFAULT_PERIOD, LOCAL_TZ, Period

SEASONS = {
    12: "Winter",
    1: "Winter",
    2: "Winter",
    3: "Frühling",
    4: "Frühling",
    5: "Frühling",
    6: "Sommer",
    7: "Sommer",
    8: "Sommer",
    9: "Herbst",
    10: "Herbst",
    11: "Herbst",
}

FEATURE_COLUMNS = [
    "timestamp",
    "timestamp_local",
    "date",
    "price",
    "wind_offshore",
    "wind_onshore",
    "wind",
    "solar",
    "load",
    "year",
    "quarter",
    "month",
    "day",
    "hour",
    "day_of_week",
    "is_weekend",
    "season",
    "renewable_generation",
    "residual_load",
    "renewable_share_pct",
    "price_lag_1",
    "price_lag_24",
    "price_lag_168",
    "price_rolling_mean_24h",
    "price_rolling_std_24h",
    "is_negative_price",
]


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    local = df["timestamp"].dt.tz_convert(LOCAL_TZ)
    df["timestamp_local"] = local.dt.tz_localize(None)
    df["date"] = df["timestamp_local"].dt.normalize()
    df["year"] = local.dt.year
    df["quarter"] = local.dt.quarter
    df["month"] = local.dt.month
    df["day"] = local.dt.day
    df["hour"] = local.dt.hour
    df["day_of_week"] = local.dt.day_of_week  # 0 = Montag
    df["is_weekend"] = df["day_of_week"] >= 5
    df["season"] = df["month"].map(SEASONS)
    return df


def add_energy_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["renewable_generation"] = df["wind"] + df["solar"]
    # Residuallast: Nachfrage, die nicht durch Wind und Solar gedeckt wird
    df["residual_load"] = df["load"] - df["renewable_generation"]
    # Kann > 100 % sein, wenn Wind + Solar die Last übersteigen (Export/Speicher)
    df["renewable_share_pct"] = df["renewable_generation"] / df["load"] * 100
    return df


def add_price_features(df: pd.DataFrame) -> pd.DataFrame:
    """Lag- und Rolling-Features. Erwartet eine lückenlose, sortierte Stundenreihe."""
    df = df.sort_values("timestamp").copy()
    price = df["price"]
    for lag in (1, 24, 168):
        df[f"price_lag_{lag}"] = price.shift(lag)
    past = price.shift(1)
    df["price_rolling_mean_24h"] = past.rolling(24).mean()
    df["price_rolling_std_24h"] = past.rolling(24).std()
    df["is_negative_price"] = price < 0
    return df


def build_features(hourly: pd.DataFrame, period: Period = DEFAULT_PERIOD) -> pd.DataFrame:
    """Erzeugt alle Features und schneidet anschließend auf den Untersuchungszeitraum zu.

    Lag-Features werden *vor* dem Zuschnitt berechnet, sodass auch die ersten
    Stunden des Zeitraums gültige Werte erhalten, sofern Historie vorhanden ist.
    """
    df = add_price_features(add_energy_features(add_calendar_features(hourly)))
    mask = (df["timestamp"] >= period.start_ts) & (df["timestamp"] < period.end_ts)
    return df.loc[mask, FEATURE_COLUMNS].reset_index(drop=True)
