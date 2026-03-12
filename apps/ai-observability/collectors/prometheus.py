import logging
from typing import Any, Dict, List
import requests
import time

from .base import BaseCollector

class PrometheusCollector(BaseCollector):
    """Collector for Prometheus metrics."""

    MAX_RESULTS = 20  # Reduced for token limits

    RESOURCE_QUERIES = {
        "node": {
            "cpu_pct": 'avg_over_time(100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)[1h:5m])',
            "memory_pct": 'avg_over_time((node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100[1h:5m])',
        },
        "pod": {
            "restart_spikes": 'sum(increase(kube_pod_container_status_restarts_total[1h])) by (namespace,pod)',
            "oom_killed": 'sum_over_time(kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}[1h])',
            "crashloopbackoff": 'sum_over_time(kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff"}[1h])',
        },
        "namespace": {
            "cpu_usage": 'avg_over_time(sum(rate(container_cpu_usage_seconds_total{container!=""}[5m])) by (namespace)[1h:5m])',
            "memory_usage": 'avg_over_time(sum(container_memory_working_set_bytes{container!=""}) by (namespace)[1h:5m])',
        },
    }

    def __init__(self, config):
        super().__init__(config)
        self.prometheus_url = config.PROMETHEUS_URL
        self.timeout = config.HTTP_TIMEOUT_SECONDS
        self.log = config.log or logging.getLogger(__name__)
        self.session = requests.Session()

    def collect(self) -> Dict[str, Any]:
        self.log.info("Collecting Prometheus metrics for last hour...")
        results = {}
        for rtype, queries in self.RESOURCE_QUERIES.items():
            results[rtype] = {}
            for metric_name, query in queries.items():
                data = self._prom_query_range(query)
                results[rtype][metric_name] = self._simplify(data)
        return results

    def _prom_query_range(self, query: str) -> List[Dict]:
        url = f"{self.prometheus_url}/api/v1/query_range"
        now = int(time.time())
        start = now - 3600  # Last hour
        step = 300  # 5 minutes
        try:
            r = self.session.get(url, params={
                "query": query,
                "start": start,
                "end": now,
                "step": step
            }, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if data.get("status") != "success":
                self.log.warning("Prometheus returned non-success for query: %s", query)
                return []
            return data["data"]["result"]
        except Exception as e:
            self.log.error("Prometheus query_range failed: %s", e)
            return []

    def _simplify(self, result_list: List[Dict]) -> List[Dict]:
        simplified = []
        for item in result_list[: self.MAX_RESULTS]:
            metric = dict(item.get("metric", {}))
            values = item.get("values", [])
            if values:
                # Calculate statistics for the time series
                values_only = [float(v[1]) for v in values if len(v) == 2 and v[1] != 'NaN']
                if values_only:
                    metric["avg"] = round(sum(values_only) / len(values_only), 2)
                    metric["min"] = round(min(values_only), 2)
                    metric["max"] = round(max(values_only), 2)
                    metric["count"] = len(values_only)
                else:
                    metric["avg"] = None
                    metric["min"] = None
                    metric["max"] = None
                    metric["count"] = 0
            else:
                metric["avg"] = None
                metric["min"] = None
                metric["max"] = None
                metric["count"] = 0
            simplified.append(metric)
        return simplified