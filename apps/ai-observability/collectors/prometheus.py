"""Prometheus collector for metrics data."""

import requests
from typing import Any, Dict, List
from datetime import datetime, timedelta, timezone

from .base import BaseCollector


class PrometheusCollector(BaseCollector):
    """Collector for Prometheus metrics."""

    def collect(self) -> Dict[str, Any]:
        """Collect key cluster metrics from Prometheus."""
        log = self.config.get('log', print)
        log.info("Collecting Prometheus metrics …")

        hours = self.config.get('LOOKBACK_HOURS', 24)

        # Cluster-level resource usage
        cpu_usage = self._prom_query(
            'sum(rate(container_cpu_usage_seconds_total{container!=""}[5m])) by (namespace)'
        )
        mem_usage = self._prom_query(
            'sum(container_memory_working_set_bytes{container!=""}) by (namespace)'
        )
        node_cpu = self._prom_query(
            '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
        )
        node_mem_pct = self._prom_query(
            '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'
        )

        # Pod health
        pod_restarts = self._prom_query(
            f'sum(increase(kube_pod_container_status_restarts_total[{hours}h])) by (namespace, pod) > 0'
        )
        pod_not_running = self._prom_query(
            'kube_pod_status_phase{phase!~"Running|Succeeded"}'
        )

        # API server latency (P99)
        api_latency = self._prom_query(
            'histogram_quantile(0.99, sum(rate(apiserver_request_duration_seconds_bucket[5m])) by (le, verb))'
        )

        # PVC usage
        pvc_usage = self._prom_query(
            '(kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes) * 100'
        )

        def _simplify(result_list: List[Dict], value_index: int = 1) -> List[Dict]:
            """Convert Prometheus result to a compact list of dicts."""
            out: List[Dict[str, Any]] = []
            for item in result_list:
                entry = dict(item.get("metric", {}))
                val = item.get("value", item.get("values", [[None, "N/A"]]))
                if isinstance(val, list) and val and isinstance(val[0], list):
                    last_sample: list = val[-1]  # innermost sample pair [timestamp, value]
                    entry["value"] = last_sample[value_index]
                elif isinstance(val, list) and len(val) == 2:
                    entry["value"] = val[value_index]
                out.append(entry)
            return out[:20]  # cap to avoid oversized prompts

        return {
            "cpu_by_namespace": _simplify(cpu_usage),
            "memory_by_namespace_mb": [
                {**d, "value": f"{float(d['value'])/1024/1024:.1f} MB"}
                for d in _simplify(mem_usage)
            ],
            "node_cpu_pct": _simplify(node_cpu),
            "node_memory_pct": _simplify(node_mem_pct),
            "pod_restarts": _simplify(pod_restarts),
            "unhealthy_pods": _simplify(pod_not_running),
            "api_latency_p99_seconds": _simplify(api_latency),
            "pvc_usage_pct": _simplify(pvc_usage),
        }

    def _prom_query(self, query: str) -> List[Dict]:
        """Execute an instant PromQL query and return the result list."""
        url = f"{self.config['PROMETHEUS_URL']}/api/v1/query"
        try:
            resp = requests.get(
                url,
                params={"query": query},
                timeout=self.config.get('HTTP_TIMEOUT_SECONDS', 30),
            )
            resp.raise_for_status()
            data = resp.json()
            if data["status"] != "success":
                log = self.config.get('log', print)
                log.warning("Prometheus query '%s' returned non-success status: %s", query, data["status"])
                return []
            return data["data"]["result"]
        except Exception as exc:
            log = self.config.get('log', print)
            log.error("Prometheus query failed: %s – %s", query, exc)
            return []

    def _prom_range_query(self, query: str, hours: int) -> List[Dict]:
        """Execute a range PromQL query over the last N hours."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=hours)
        url = f"{self.config['PROMETHEUS_URL']}/api/v1/query_range"
        try:
            resp = requests.get(
                url,
                params={
                    "query": query,
                    "start": start.timestamp(),
                    "end": end.timestamp(),
                    "step": "5m",
                },
                timeout=self.config.get('HTTP_TIMEOUT_SECONDS', 30),
            )
            resp.raise_for_status()
            data = resp.json()
            if data["status"] != "success":
                return []
            return data["data"]["result"]
        except Exception as exc:
            log = self.config.get('log', print)
            log.error("Prometheus range query failed: %s – %s", query, exc)
            return []
