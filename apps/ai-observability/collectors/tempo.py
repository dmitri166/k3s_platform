"""Tempo collector for trace data."""

import requests
from typing import Any, Dict
from datetime import datetime, timezone, timedelta

from .base import BaseCollector


class TempoCollector(BaseCollector):
    """Collector for Tempo traces."""

    def collect(self) -> Dict[str, Any]:
        """Query Tempo for traces in the last hour."""
        log = self.config.get('log', print)
        log.info("Collecting Tempo traces …")

        # Correct Tempo search endpoint
        search_url = f"{self.config['TEMPO_URL']}/api/traces/search"

        # Compute nanosecond timestamps
        end = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)  # current time in ns
        start = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() * 1_000_000_000)  # 1 hour ago

        try:
            resp = requests.get(
                search_url,
                params={
                    "start": start,
                    "end": end,
                    "limit": 20,
                },
                timeout=self.config.get('HTTP_TIMEOUT_SECONDS', 30),
            )
            resp.raise_for_status()
            traces = resp.json().get("traces", [])
        except Exception as exc:
            log.error("Tempo search failed: %s", exc)
            traces = []

        return {
            "error_traces": traces,
        }