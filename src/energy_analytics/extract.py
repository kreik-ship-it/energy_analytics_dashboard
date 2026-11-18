"""Datenabruf über die öffentliche Energy-Charts API.

Die API ist rate-limitiert (HTTP 429). Der Client wiederholt Anfragen deshalb
mit exponentiellem Backoff und ruft lange Zeiträume jahresweise ab.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator

import pandas as pd
import requests

from .config import API_BASE_URL, BIDDING_ZONE, COUNTRY, PRODUCTION_TYPES

logger = logging.getLogger(__name__)


class EnergyChartsClient:
    """Minimaler Client für die Endpunkte ``/price`` und ``/public_power``."""

    def __init__(
        self,
        base_url: str = API_BASE_URL,
        timeout: int = 60,
        max_retries: int = 5,
        backoff_seconds: float = 5.0,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.session = session or requests.Session()

    def _get(self, endpoint: str, params: dict) -> dict:
        url = f"{self.base_url}/{endpoint}"
        for attempt in range(1, self.max_retries + 1):
            response = self.session.get(url, params=params, timeout=self.timeout)
            if response.status_code == 429 or response.status_code >= 500:
                wait = self.backoff_seconds * 2 ** (attempt - 1)
                logger.warning(
                    "%s -> HTTP %s, neuer Versuch in %.0f s (%d/%d)",
                    endpoint,
                    response.status_code,
                    wait,
                    attempt,
                    self.max_retries,
                )
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()
        raise RuntimeError(
            f"{endpoint}: keine erfolgreiche Antwort nach {self.max_retries} Versuchen"
        )

    def fetch_prices(self, start: str, end: str, bzn: str = BIDDING_ZONE) -> pd.DataFrame:
        """Day-Ahead-Preise (EUR/MWh) als DataFrame mit UTC-Zeitstempel."""
        frames = [
            prices_to_frame(self._get("price", {"bzn": bzn, "start": s, "end": e}))
            for s, e in yearly_chunks(start, end)
        ]
        return _concat(frames)

    def fetch_public_power(self, start: str, end: str, country: str = COUNTRY) -> pd.DataFrame:
        """Wind-, Solar-Erzeugung und Last (MW) als DataFrame mit UTC-Zeitstempel."""
        frames = [
            public_power_to_frame(
                self._get("public_power", {"country": country, "start": s, "end": e})
            )
            for s, e in yearly_chunks(start, end)
        ]
        return _concat(frames)


def yearly_chunks(start: str, end: str) -> Iterator[tuple[str, str]]:
    """Zerlegt ``[start, end)`` in Abschnitte von höchstens einem Kalenderjahr."""
    current = pd.Timestamp(start)
    stop = pd.Timestamp(end)
    while current < stop:
        nxt = min(pd.Timestamp(year=current.year + 1, month=1, day=1), stop)
        yield current.strftime("%Y-%m-%d"), nxt.strftime("%Y-%m-%d")
        current = nxt


def prices_to_frame(payload: dict) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(payload["unix_seconds"], unit="s", utc=True),
            "price": payload["price"],
        }
    )


def public_power_to_frame(payload: dict) -> pd.DataFrame:
    df = pd.DataFrame({"timestamp": pd.to_datetime(payload["unix_seconds"], unit="s", utc=True)})
    available = {pt["name"]: pt["data"] for pt in payload["production_types"]}
    missing = set(PRODUCTION_TYPES) - set(available)
    if missing:
        raise ValueError(f"Erzeugungsarten fehlen in der API-Antwort: {sorted(missing)}")
    for api_name, column in PRODUCTION_TYPES.items():
        df[column] = available[api_name]
    return df


def _concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
    df = pd.concat(frames, ignore_index=True)
    return (
        df.drop_duplicates(subset="timestamp", keep="last")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
