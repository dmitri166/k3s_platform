"""Tempo collector for trace data."""

import requests
from typing import Any, Dict, List
from datetime import datetime, timezone, timedelta

from .base import BaseCollector


class TempoCollector(BaseCollector):
    """Collector for Tempo traces."""

    def collect(self) -> Dict[str, Any]:
        """Query Tempo for highest latency spans/errors."""
        log = self.config.get('log', print)
        log.info("Collecting Tempo traces …")

        # For simplicity, query for traces with errors or high latency in the last hour
        # Tempo search API example
        search_url = f"{self.config['TEMPO_URL']}/api/search"
        start = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() * 1000000)  # microseconds
        end = int(datetime.now(timezone.utc).timestamp() * 1000000)

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
            data = resp.json()
            traces = data.get("traces", [])
        except Exception as exc:
            log.error("Tempo search failed: %s", exc)
            traces = []

        # Also, query for high latency spans, but for now, return the traces
        return {
            "error_traces": traces,
        }
