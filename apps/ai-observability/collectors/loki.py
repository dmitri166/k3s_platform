import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
import requests

from .base import BaseCollector

class LokiCollector(BaseCollector):
    """Collector for Loki logs."""

    def collect(self) -> Dict[str, Any]:
        log = self.config.get("log", logging.getLogger(__name__))
        log.info("Collecting Loki logs…")

        now = datetime.now(timezone.utc)
        start_ns = int((now - timedelta(hours=self.config.get("LOOKBACK_HOURS", 24))).timestamp() * 1e9)
        end_ns = int(now.timestamp() * 1e9)

        queries = {
            "recent_errors": '{namespace=~".+"} |= "error" | line_format "{{.namespace}} {{.pod}} {{.line}}"',
            "recent_warnings": '{namespace=~".+"} |= "warning" | line_format "{{.namespace}} {{.pod}} {{.line}}"',
            "oom_events": '{namespace=~".+"} |= "OOMKilled"',
            "crashloop_events": '{namespace=~".+"} |~ "CrashLoopBackOff|BackOff"',
        }

        results = {}
        for key, q in queries.items():
            results[key] = self._loki_query(q, start_ns=start_ns, end_ns=end_ns, limit=50 if "warnings" in key else 100)

        return results

    def _loki_query(self, logql: str, start_ns: int, end_ns: int, limit: int = 50) -> List[str]:
        url = f"{self.config['LOKI_URL']}/loki/api/v1/query_range"
        log = self.config.get("log", logging.getLogger(__name__))
        try:
            resp = requests.get(
                url,
                params={
                    "query": logql,
                    "start": start_ns,
                    "end": end_ns,
                    "limit": limit,
                    "direction": "backward",
                },
                timeout=self.config.get("HTTP_TIMEOUT_SECONDS", 30),
            )
            resp.raise_for_status()
            data = resp.json()
            lines: List[str] = []
            for stream in data.get("data", {}).get("result", []):
                for _, line in stream.get("values", []):
                    lines.append(line)
            return lines
        except Exception as exc:
            log.error("Loki query failed (%s): %s", logql, exc)
            return []