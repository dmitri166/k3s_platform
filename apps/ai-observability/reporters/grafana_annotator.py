"""Grafana annotator for pushing annotations to Grafana."""

import requests
from typing import Any, Dict
from datetime import datetime, timezone


def annotate_grafana(title: str, text: str, tags: list, config: Dict[str, Any]):
    """Push an annotation to Grafana."""
    grafana_url = config.get('GRAFANA_URL')
    api_key = config.get('GRAFANA_API_KEY')
    if not grafana_url or not api_key:
        log = config.get('log', print)
        log.warning("Grafana URL or API key not configured, skipping annotation.")
        return

    url = f"{grafana_url}/api/annotations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "dashboardId": 0,  # Global annotation
        "panelId": 0,
        "time": int(datetime.now(timezone.utc).timestamp() * 1000),  # milliseconds
        "timeEnd": int(datetime.now(timezone.utc).timestamp() * 1000),
        "tags": tags,
        "text": text,
    }

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        resp.raise_for_status()
        log = config.get('log', print)
        log.info("Annotation pushed to Grafana: %s", title)
    except Exception as exc:
        log = config.get('log', print)
        log.error("Failed to push Grafana annotation: %s", exc)
