import requests
from typing import Any, Dict
from datetime import datetime, timezone

def annotate_grafana(title: str, text: str, tags: list, config: Dict[str, Any]):
    grafana_url = config.get('GRAFANA_URL')
    api_key = config.get('GRAFANA_API_KEY')
    log = config.get('log', print)

    if not grafana_url or not api_key:
        log.warning("Grafana URL or API key not configured, skipping annotation.")
        return

    url = f"{grafana_url}/api/annotations"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    data = {"dashboardId": 0, "panelId": 0, "time": now_ms, "timeEnd": now_ms, "tags": tags, "text": text}

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        resp.raise_for_status()
        log.info("Annotation pushed to Grafana: %s", title)
    except Exception as exc:
        log.error("Failed to push Grafana annotation: %s", exc)