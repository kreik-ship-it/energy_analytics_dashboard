"""End-to-end-Pipeline: API -> Rohdaten -> Stundendaten -> Features -> SQLite.

Aufruf::

    python -m energy_analytics.pipeline              # nutzt vorhandene Rohdaten
    python -m energy_analytics.pipeline --refresh    # lädt Rohdaten neu von der API
"""

from __future__ import annotations

import argparse
import logging

from . import config
from .database import write_database
from .extract import EnergyChartsClient
from .features import build_features
from .transform import build_hourly_dataset, quality_report, read_raw_csv

logger = logging.getLogger("energy_analytics")


def extract(period: config.Period = config.DEFAULT_PERIOD, refresh: bool = False) -> None:
    if not refresh and config.RAW_PRICE_FILE.exists() and config.RAW_POWER_FILE.exists():
        logger.info("Rohdaten vorhanden – überspringe API-Abruf (--refresh erzwingt Neuladen)")
        return
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    client = EnergyChartsClient()
    logger.info("Lade Day-Ahead-Preise %s bis %s", period.fetch_start, period.end)
    client.fetch_prices(period.fetch_start, period.end).to_csv(config.RAW_PRICE_FILE, index=False)
    logger.info("Lade Erzeugung und Last %s bis %s", period.fetch_start, period.end)
    client.fetch_public_power(period.fetch_start, period.end).to_csv(
        config.RAW_POWER_FILE, index=False
    )


def run(refresh: bool = False, period: config.Period = config.DEFAULT_PERIOD) -> None:
    extract(period, refresh=refresh)

    prices = read_raw_csv(config.RAW_PRICE_FILE)
    power = read_raw_csv(config.RAW_POWER_FILE)
    hourly = build_hourly_dataset(prices, power, period)

    report = quality_report(hourly)
    logger.info("Datenqualität Stundendatensatz:\n%s", report)
    if not report.ok:
        raise ValueError("Datenqualitätsprüfung fehlgeschlagen – siehe Report")

    features = build_features(hourly, period)
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    hourly.to_csv(config.HOURLY_FILE, index=False)
    features.to_csv(config.FEATURES_FILE, index=False)

    db_path = write_database(features)
    logger.info("%s Stunden in %s geschrieben", f"{len(features):,}", db_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="Rohdaten neu von der API laden")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(refresh=args.refresh)


if __name__ == "__main__":
    main()
