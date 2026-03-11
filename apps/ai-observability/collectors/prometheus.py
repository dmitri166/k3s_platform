"""Advanced Prometheus collector for AI observability."""

import logging
from typing import Any, Dict, List
from datetime import datetime, timedelta, timezone

import requests

from .base import BaseCollector


class PrometheusCollector(BaseCollector):

    MAX_RESULTS = 20

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        self.prometheus_url = config["PROMETHEUS_URL"]
        self.timeout = config.get("HTTP_TIMEOUT_SECONDS", 30)
        self.log = config.get("log") or logging.getLogger(__name__)
        self.session = requests.Session()

    def collect(self) -> Dict[str, Any]:

        self.log.info("Collecting Prometheus metrics")

        hours = int(self.config.get("LOOKBACK_HOURS", 24))

        queries = {

            # Core resource metrics
            "cpu_by_namespace":
                'sum(rate(container_cpu_usage_seconds_total{container!=""}[5m])) by (namespace)',

            "memory_by_namespace":
                'sum(container_memory_working_set_bytes{container!=""}) by (namespace)',

            "node_cpu_pct":
                '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',

            "node_memory_pct":
                '(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100',

            # Pod health
            "pod_restart_spikes":
                'sum(increase(kube_pod_container_status_restarts_total[10m])) by (namespace,pod)',

            "crashloopbackoff":
                'kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff"}',

            "oom_killed":
                'kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}',

            "unhealthy_pods":
                'kube_pod_status_phase{phase!~"Running|Succeeded"}',

            "pending_pods":
                'kube_pod_status_phase{phase="Pending"}',

            # Storage
            "pvc_usage_pct":
                '(kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes) * 100',

            # Kubernetes API health
            "api_latency_p99":
                'histogram_quantile(0.99, sum(rate(apiserver_request_duration_seconds_bucket[5m])) by (le, verb))',

            "api_error_rate":
                'rate(apiserver_request_total{code=~"5.."}[5m])',

        }

        results = {}

        for key, query in queries.items():

            data = self._prom_query(query)

            simplified = self._simplify(data)

            if key == "memory_by_namespace":
                simplified = self._convert_memory_mb(simplified)

            results[key] = simplified

        return results

    # -------------------------------------

    def _prom_query(self, query: str) -> List[Dict]:

        url = f"{self.prometheus_url}/api/v1/query"

        try:

            r = self.session.get(
                url,
                params={"query": query},
                timeout=self.timeout,
            )

            r.raise_for_status()

            data = r.json()

            if data.get("status") != "success":

                self.log.warning("Prometheus returned non-success for %s", query)

                return []

            return data["data"]["result"]

        except Exception as e:

            self.log.error("Prometheus query failed: %s", e)

            return []

    # -------------------------------------

    def _simplify(self, result_list: List[Dict]) -> List[Dict]:

        simplified = []

        for item in result_list:

            metric = item.get("metric", {})

            entry = dict(metric)

            value = item.get("value")

            try:
                if value and len(value) == 2:
                    entry["value"] = float(value[1])
                else:
                    entry["value"] = None
            except:
                entry["value"] = None

            simplified.append(entry)

        return simplified[: self.MAX_RESULTS]

    # -------------------------------------

    def _convert_memory_mb(self, metrics: List[Dict]) -> List[Dict]:

        for m in metrics:

            val = m.get("value")

            if isinstance(val, (int, float)):

                m["value_mb"] = round(val / 1024 / 1024, 2)

        return metrics