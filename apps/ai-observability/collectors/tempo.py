from datetime import datetime, timezone, timedelta
from typing import Any, Dict
import requests
import logging

from .base import BaseCollector

class TempoCollector(BaseCollector):
    """Collector for Tempo traces."""

    def collect(self) -> Dict[str, Any]:
        log = self.config.get("log", logging.getLogger(__name__))
        log.info("Collecting Tempo traces…")

        now = datetime.now(timezone.utc)
        start_ms = int((now - timedelta(hours=self.config.get("LOOKBACK_HOURS", 1))).timestamp() * 1000)
        end_ms = int(now.timestamp() * 1000)

        search_url = f"{self.config['TEMPO_URL']}/api/traces/search"
        try:
            resp = requests.get(
                search_url,
                params={"start": start_ms, "end": end_ms, "limit": 20},
                timeout=self.config.get("HTTP_TIMEOUT_SECONDS", 30),
            )
            resp.raise_for_status()
            data = resp.json()
            traces = data.get("traces", [])
            return {"error_traces": traces}
        except Exception as exc:
            log.error("Tempo query failed: %s", exc)
            return {"error_traces": []}