"""Advanced Prometheus collector mapping metrics to all Kubernetes resources."""

import logging
from typing import Any, Dict, List
import requests

from .base import BaseCollector

class PrometheusCollector(BaseCollector):
    """Collector for Prometheus metrics."""

    MAX_RESULTS = 50

    RESOURCE_QUERIES = {
        "node": {
            "cpu_pct": '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
            "memory_pct": '(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100',
        },
        "pod": {
            "restart_spikes": 'sum(increase(kube_pod_container_status_restarts_total[10m])) by (namespace,pod)',
            "oom_killed": 'kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}',
            "crashloopbackoff": 'kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff"}',
        },
        "namespace": {
            "cpu_usage": 'sum(rate(container_cpu_usage_seconds_total{container!=""}[5m])) by (namespace)',
            "memory_usage": 'sum(container_memory_working_set_bytes{container!=""}) by (namespace)',
        },
    }

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.prometheus_url = config["PROMETHEUS_URL"]
        self.timeout = config.get("HTTP_TIMEOUT_SECONDS", 30)
        self.log = config.get("log") or logging.getLogger(__name__)
        self.session = requests.Session()

    def collect(self) -> Dict[str, Any]:
        self.log.info("Collecting Prometheus metrics for all resources...")
        results = {}
        for rtype, queries in self.RESOURCE_QUERIES.items():
            results[rtype] = {}
            for metric_name, query in queries.items():
                data = self._prom_query(query)
                results[rtype][metric_name] = self._simplify(data)
        return results

    def _prom_query(self, query: str) -> List[Dict]:
        url = f"{self.prometheus_url}/api/v1/query"
        try:
            r = self.session.get(url, params={"query": query}, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if data.get("status") != "success":
                self.log.warning("Prometheus returned non-success for query: %s", query)
                return []
            return data["data"]["result"]
        except Exception as e:
            self.log.error("Prometheus query failed: %s", e)
            return []

    def _simplify(self, result_list: List[Dict]) -> List[Dict]:
        simplified = []
        for item in result_list[: self.MAX_RESULTS]:
            metric = dict(item.get("metric", {}))
            val = item.get("value")
            if val and len(val) == 2:
                metric["value"] = float(val[1])
            else:
                metric["value"] = None
            simplified.append(metric)
        return simplified