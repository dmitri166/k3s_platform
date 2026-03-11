"""Tempo collector for trace data."""

import requests
from typing import Any, Dict
from datetime import datetime, timezone, timedelta

from .base import BaseCollector


class TempoCollector(BaseCollector):
    """Collector for Tempo traces."""

    def collect(self) -> Dict[str, Any]:
        """Query Tempo for highest latency spans/errors."""
        log = self.config.get("log", print)
        log.info("Collecting Tempo traces …")

        # Use last 1 hour for search window
        now = datetime.now(timezone.utc)
        start = int((now - timedelta(hours=1)).timestamp() * 1000)  # milliseconds
        end = int(now.timestamp() * 1000)

        search_url = f"{self.config['TEMPO_URL']}/api/search"
        traces: list = []

        try:
            resp = requests.get(
                search_url,
                params={
                    "start": start,
                    "end": end,
                    "limit": 20,
                },
                timeout=self.config.get("HTTP_TIMEOUT_SECONDS", 30),
            )
            resp.raise_for_status()
            data = resp.json()
            traces = data.get("traces", [])

            if not traces:
                log.info("No traces found in the last hour.")
            else:
                log.info("Collected %d traces.", len(traces))

        except requests.exceptions.HTTPError as exc:
            log.error("Tempo HTTP error: %s", exc)
        except requests.exceptions.RequestException as exc:
            log.error("Tempo request failed: %s", exc)
        except ValueError as exc:
            log.error("Failed to parse Tempo response JSON: %s", exc)
        except Exception as exc:
            log.error("Unexpected error collecting Tempo traces: %s", exc)

        return {
            "error_traces": traces,
        }