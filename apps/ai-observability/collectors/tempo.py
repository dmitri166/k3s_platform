import requests
import time
from typing import Any, Dict
from .base import BaseCollector

class TempoCollector(BaseCollector):
    """Collector for Tempo traces."""

    def collect(self) -> Dict[str, Any]:
        log = self.config.get('log', print)
        log.info("Collecting Tempo traces …")

        # Use time.time_ns() to get current time in nanoseconds
        end = time.time_ns()
        start = end - (1 * 60 * 60 * 1_000_000_000)  # 1 hour before

        search_url = f"{self.config['TEMPO_URL']}/api/search"

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

        return {"error_traces": traces}