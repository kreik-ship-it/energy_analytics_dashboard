"""Hilfsfunktionen für die Day-Ahead-Preisprognose.

Realistisches Setup: Die Day-Ahead-Auktion für Tag D schließt am Mittag von
Tag D-1. Zu diesem Zeitpunkt sind alle Preise bis einschließlich Tag D-1
bekannt, nicht aber die Preise von Tag D. ``price_lag_1`` wäre daher ein
Informationsleck und wird **nicht** verwendet; zulässig sind Lags >= 24 h.

Für Wind, Solar und Last werden die Ist-Werte als Näherung für die am Vortag
verfügbaren Prognosen genutzt (Annahme "perfekte Prognose", siehe README).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MODEL_FEATURES = [
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
    "wind",
    "solar",
    "load",
    "residual_load",
    "renewable_share_pct",
    "price_lag_24",
    "price_lag_168",
    "price_prev_day_mean",
    "price_prev_day_std",
]
TARGET = "price"


def add_forecast_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ergänzt Kennzahlen, die zum Auktionszeitpunkt (D-1, 12 Uhr) bekannt sind."""
    df = df.sort_values("timestamp").copy()
    known = df["price"].shift(24)
    df["price_prev_day_mean"] = known.rolling(24).mean()
    df["price_prev_day_std"] = known.rolling(24).std()
    df["is_weekend"] = df["is_weekend"].astype(int)
    return df


def time_split(df: pd.DataFrame, test_start: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Zeitlicher Train/Test-Split (keine Durchmischung -> kein Leakage)."""
    cutoff = pd.Timestamp(test_start, tz="Europe/Berlin")
    df = df.dropna(subset=MODEL_FEATURES + [TARGET])
    return df[df["timestamp"] < cutoff], df[df["timestamp"] >= cutoff]


def evaluate(y_true, y_pred) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_pred - y_true
    return {
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(np.sqrt(np.mean(err**2))),
        "Bias": float(np.mean(err)),
    }
