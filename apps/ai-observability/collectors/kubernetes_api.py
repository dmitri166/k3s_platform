"""Kubernetes API collector for events."""

from kubernetes import client, config
from typing import Any, Dict, List
from datetime import datetime, timezone, timedelta

from .base import BaseCollector


class KubernetesAPICollector(BaseCollector):
    """Collector for Kubernetes events."""

    def collect(self) -> Dict[str, Any]:
        """Query Kubernetes API for events."""
        log = self.config.get('log', print)
        log.info("Collecting Kubernetes events …")

        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()

        v1 = client.CoreV1Api()
        events = v1.list_event_for_all_namespaces(
            field_selector="type=Warning",
            timeout_seconds=30
        )

        recent_events = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.config.get('LOOKBACK_HOURS', 24))
        for event in events.items:
            event_time = event.last_timestamp or event.first_timestamp
            if event_time and event_time.replace(tzinfo=timezone.utc) > cutoff:
                recent_events.append({
                    "namespace": event.metadata.namespace,
                    "name": event.metadata.name,
                    "reason": event.reason,
                    "message": event.message,
                    "source": event.source.component if event.source else None,
                    "count": event.count,
                    "last_seen": str(event.last_timestamp),
                })

        return {
            "recent_events": recent_events[:50],  # Limit to 50
        }
