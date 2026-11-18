import numpy as np
import pandas as pd
import pytest

from energy_analytics.config import Period

# Zeitraum über die Zeitumstellung am 26.03.2023 (Sommerzeit, 23-Stunden-Tag)
TEST_PERIOD = Period(start="2023-03-20", end="2023-04-03", history_days=8)


@pytest.fixture
def period() -> Period:
    return TEST_PERIOD


@pytest.fixture
def raw_power() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    ts = pd.date_range(
        "2023-03-12", "2023-04-03", freq="15min", tz="Europe/Berlin", inclusive="left"
    ).tz_convert("UTC")
    n = len(ts)
    hour = ts.tz_convert("Europe/Berlin").hour
    solar = np.clip(np.sin((hour - 6) / 12 * np.pi), 0, None) * 30_000
    return pd.DataFrame(
        {
            "timestamp": ts,
            "wind_offshore": rng.uniform(0, 8_000, n),
            "wind_onshore": rng.uniform(1_000, 40_000, n),
            "solar": solar,
            "load": rng.uniform(40_000, 70_000, n),
        }
    )


@pytest.fixture
def raw_prices() -> pd.DataFrame:
    """Stündliche Preise, analog zur API vor Einführung der 15-Minuten-Produkte."""
    rng = np.random.default_rng(7)
    ts = pd.date_range(
        "2023-03-12", "2023-04-03", freq="1h", tz="Europe/Berlin", inclusive="left"
    ).tz_convert("UTC")
    return pd.DataFrame({"timestamp": ts, "price": rng.normal(90, 40, len(ts))})
