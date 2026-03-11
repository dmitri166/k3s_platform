from datetime import datetime, timezone, timedelta
import requests

from .base import BaseCollector

class TempoCollector(BaseCollector):
    """Collector for Tempo traces."""

    def collect(self):
        log = self.config.get("log", print)
        log.info("Collecting Tempo traces …")

        search_url = f"{self.config['TEMPO_URL']}/api/traces/search"

        now = datetime.now(timezone.utc)
        start = int((now - timedelta(hours=1)).timestamp() * 1000)  # milliseconds
        end = int(now.timestamp() * 1000)

        try:
            resp = requests.get(
                search_url,
                params={"start": start, "end": end, "limit": 20},
                timeout=self.config.get("HTTP_TIMEOUT_SECONDS", 30),
            )
            resp.raise_for_status()
            data = resp.json()
            traces = data.get("traces", [])
        except Exception as exc:
            log.error("Tempo search failed: %s", exc)
            traces = []

        return {"error_traces": traces}