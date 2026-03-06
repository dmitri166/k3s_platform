"""Loki collector for log data."""

import requests
from typing import Any, Dict, List
from datetime import datetime, timezone, timedelta

from .base import BaseCollector


class LokiCollector(BaseCollector):
    """Collector for Loki logs."""

    def collect(self) -> Dict[str, Any]:
        """Query Loki for error/warning patterns over the lookback window."""
        log = self.config.get('log', print)
        log.info("Collecting Loki logs …")

        end_ns = int(datetime.now(timezone.utc).timestamp() * 1e9)
        start_ns = int((datetime.now(timezone.utc) - timedelta(hours=self.config.get('LOOKBACK_HOURS', 24))).timestamp() * 1e9)

        errors = self._loki_query(
            '{namespace=~".+"} |= "error" | line_format "{{.namespace}} {{.pod}} {{.line}}"',
            limit=100,
            start_ns=start_ns,
            end_ns=end_ns
        )
        warnings = self._loki_query(
            '{namespace=~".+"} |= "warning" | line_format "{{.namespace}} {{.pod}} {{.line}}"',
            limit=50,
            start_ns=start_ns,
            end_ns=end_ns
        )
        oom_logs = self._loki_query(
            '{namespace=~".+"} |= "OOMKilled"',
            limit=20,
            start_ns=start_ns,
            end_ns=end_ns
        )
        crash_logs = self._loki_query(
            '{namespace=~".+"} |~ "CrashLoopBackOff|BackOff"',
            limit=20,
            start_ns=start_ns,
            end_ns=end_ns
        )

        return {
            "recent_errors": errors[:50],
            "recent_warnings": warnings[:30],
            "oom_events": oom_logs,
            "crashloop_events": crash_logs,
        }

    def _loki_query(self, logql: str, limit: int = 50, start_ns: int = 0, end_ns: int = 0) -> List[str]:
        """Execute a Loki query and return lines."""
        url = f"{self.config['LOKI_URL']}/loki/api/v1/query_range"
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
                timeout=self.config.get('HTTP_TIMEOUT_SECONDS', 30),
            )
            resp.raise_for_status()
            data = resp.json()
            lines: List[str] = []
            for stream in data.get("data", {}).get("result", []):
                for _ts, line in stream.get("values", []):
                    lines.append(line)
            return lines
        except Exception as exc:
            log = self.config.get('log', print)
            log.error("Loki query failed: %s – %s", logql, exc)
            return []
