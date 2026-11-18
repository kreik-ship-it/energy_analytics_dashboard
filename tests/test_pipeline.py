from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from energy_analytics.config import SQL_DIR
from energy_analytics.database import build_dim_date, run_query, run_sql_file, write_database
from energy_analytics.extract import public_power_to_frame, yearly_chunks
from energy_analytics.features import build_features
from energy_analytics.modeling import MODEL_FEATURES, add_forecast_features, evaluate, time_split
from energy_analytics.transform import build_hourly_dataset, quality_report, to_hourly


# --- Extract -----------------------------------------------------------------
def test_yearly_chunks_split_at_year_boundaries():
    assert list(yearly_chunks("2022-12-24", "2025-01-01")) == [
        ("2022-12-24", "2023-01-01"),
        ("2023-01-01", "2024-01-01"),
        ("2024-01-01", "2025-01-01"),
    ]


def test_public_power_payload_is_mapped_to_columns():
    payload = {
        "unix_seconds": [1672527600, 1672528500],
        "production_types": [
            {"name": "Wind offshore", "data": [1.0, 2.0]},
            {"name": "Wind onshore", "data": [3.0, 4.0]},
            {"name": "Solar", "data": [0.0, 0.0]},
            {"name": "Load", "data": [50.0, 51.0]},
            {"name": "Nuclear", "data": [0.0, 0.0]},
        ],
    }
    df = public_power_to_frame(payload)
    assert list(df.columns) == ["timestamp", "wind_offshore", "wind_onshore", "solar", "load"]
    assert str(df["timestamp"].dt.tz) == "UTC"


def test_public_power_missing_type_raises():
    payload = {"unix_seconds": [0], "production_types": [{"name": "Solar", "data": [0]}]}
    with pytest.raises(ValueError, match="fehlen"):
        public_power_to_frame(payload)


# --- Transform ---------------------------------------------------------------
def test_quarter_hours_are_averaged_to_hours():
    ts = pd.date_range("2025-10-01 00:00", periods=8, freq="15min", tz="UTC")
    df = pd.DataFrame({"timestamp": ts, "price": [10, 20, 30, 40, 0, 0, 0, 4]})
    hourly = to_hourly(df)
    assert hourly["price"].tolist() == [25.0, 1.0]


def test_hourly_dataset_is_complete_across_dst_change(raw_prices, raw_power, period):
    hourly = build_hourly_dataset(raw_prices, raw_power, period, include_history=False)
    report = quality_report(hourly)
    assert report.ok
    # 14 Tage, davon ein 23-Stunden-Tag (Umstellung auf Sommerzeit)
    assert report.rows == 14 * 24 - 1


# --- Features ----------------------------------------------------------------
@pytest.fixture
def features(raw_prices, raw_power, period):
    return build_features(build_hourly_dataset(raw_prices, raw_power, period), period)


def test_calendar_features_use_local_time(features):
    first = features.iloc[0]
    assert first["timestamp_local"] == pd.Timestamp("2023-03-20 00:00")
    assert first["hour"] == 0
    # Am Tag der Zeitumstellung fehlt die Stunde 2 Uhr Ortszeit
    dst_day = features[features["date"] == pd.Timestamp("2023-03-26")]
    assert len(dst_day) == 23
    assert 2 not in dst_day["hour"].values


def test_lags_are_filled_from_history(features):
    assert features["price_lag_168"].notna().all()
    assert features["price_rolling_mean_24h"].notna().all()


def test_rolling_features_do_not_use_current_price(features):
    """Das 24h-Mittel zum Zeitpunkt t darf nur Preise bis t-1 enthalten."""
    df = features.reset_index(drop=True)
    i = 30
    expected = df.loc[i - 24 : i - 1, "price"].mean()
    assert df.loc[i, "price_rolling_mean_24h"] == pytest.approx(expected)


def test_energy_features(features):
    row = features.iloc[5]
    assert row["renewable_generation"] == pytest.approx(row["wind"] + row["solar"])
    assert row["residual_load"] == pytest.approx(row["load"] - row["renewable_generation"])
    assert row["renewable_share_pct"] == pytest.approx(
        100 * row["renewable_generation"] / row["load"]
    )


# --- Datenbank + SQL ---------------------------------------------------------
@pytest.fixture
def db_path(features, tmp_path) -> Path:
    return write_database(features, db_path=tmp_path / "test.db")


def test_dim_date_covers_fact_table(db_path):
    missing = run_query(
        "SELECT COUNT(*) AS n FROM energy_data e LEFT JOIN dim_date d ON e.date = d.date "
        "WHERE d.date IS NULL",
        db_path,
    )
    assert missing["n"].iloc[0] == 0


@pytest.mark.parametrize("sql_file", sorted(p.name for p in (SQL_DIR / "analysis").glob("*.sql")))
def test_all_analysis_queries_run(db_path, sql_file):
    result = run_sql_file(sql_file, db_path)
    assert not result.empty


def test_data_quality_query_finds_no_gaps(db_path):
    result = run_sql_file("01_data_quality", db_path).iloc[0]
    assert result["total_rows"] == result["distinct_timestamps"]
    assert result["gaps"] == 0
    assert result["missing_values"] == 0


def test_views_exist(db_path):
    for view in ("v_daily_summary", "v_monthly_summary"):
        assert not run_query(f"SELECT * FROM {view}", db_path).empty


def test_build_dim_date():
    dim = build_dim_date("2024-12-30", "2025-01-05")
    assert len(dim) == 7
    assert dim.loc[0, "day_name_de"] == "Montag"
    assert dim.loc[2, "year_month_key"] == 202501


# --- Modeling ----------------------------------------------------------------
def test_forecast_features_and_split(features):
    df = add_forecast_features(features)
    train, test = time_split(df, "2023-03-30")
    assert train["timestamp"].max() < test["timestamp"].min()
    assert "price_lag_1" not in MODEL_FEATURES  # Leakage für Day-Ahead
    assert not train[MODEL_FEATURES].isna().any().any()


def test_evaluate():
    metrics = evaluate([1, 2, 3], [2, 2, 5])
    assert metrics["MAE"] == pytest.approx(1.0)
    assert metrics["RMSE"] == pytest.approx(np.sqrt(5 / 3))
    assert metrics["Bias"] == pytest.approx(1.0)


# --- Dashboard-Export --------------------------------------------------------
def test_dashboard_payload_is_aligned(db_path):
    from energy_analytics.dashboard_export import build_payload

    payload = build_payload(db_path, with_forecast=False)
    hourly = payload["hourly"]
    lengths = {len(v) for v in hourly.values()}
    assert lengths == {payload["meta"]["hours"]}
    assert hourly["day"][0] == 0
    assert payload["meta"]["first_day"] == "2023-03-20"
