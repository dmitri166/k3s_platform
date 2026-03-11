import logging
from typing import Any, Dict, List


def detect_anomalies(metrics: Dict[str, Any], logs: Dict[str, Any], traces: Dict[str, Any], events: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Detect anomalies across Prometheus metrics, Loki logs, Tempo traces, and Kubernetes events.

    Returns a dict with keys:
    - cpu
    - memory
    - pod_restarts
    - oom_killed
    - crashloop
    - unhealthy_pods
    - pending_pods
    - api_errors
    - log_errors
    - log_warnings
    - traces_errors
    """
    log = logging.getLogger("anomaly-detector")

    anomalies: Dict[str, List[Dict[str, Any]]] = {
        "cpu": [],
        "memory": [],
        "pod_restarts": [],
        "oom_killed": [],
        "crashloop": [],
        "unhealthy_pods": [],
        "pending_pods": [],
        "api_errors": [],
        "log_errors": [],
        "log_warnings": [],
        "traces_errors": [],
    }

    # ------------------------------
    # 1. CPU anomalies
    cpu_metrics = metrics.get("node_cpu_pct", [])
    for m in cpu_metrics:
        if m.get("value") is not None and m["value"] > 85:
            anomalies["cpu"].append({"node": m.get("instance"), "usage_pct": m["value"], "severity": "high"})

    # ------------------------------
    # 2. Memory anomalies
    mem_metrics = metrics.get("node_memory_pct", [])
    for m in mem_metrics:
        if m.get("value") is not None and m["value"] > 85:
            anomalies["memory"].append({"node": m.get("instance"), "usage_pct": m["value"], "severity": "high"})

    # ------------------------------
    # 3. Pod restarts
    pod_restarts = metrics.get("pod_restart_spikes", [])
    for m in pod_restarts:
        if m.get("value") and m["value"] > 3:
            anomalies["pod_restarts"].append({
                "namespace": m.get("namespace"),
                "pod": m.get("pod"),
                "restarts": m["value"],
                "severity": "medium"
            })

    # ------------------------------
    # 4. OOMKilled
    oom = metrics.get("oom_killed", [])
    for m in oom:
        anomalies["oom_killed"].append({"namespace": m.get("namespace"), "pod": m.get("pod"), "severity": "high"})

    # ------------------------------
    # 5. CrashLoopBackOff
    crash = metrics.get("crashloopbackoff", [])
    for m in crash:
        anomalies["crashloop"].append({"namespace": m.get("namespace"), "pod": m.get("pod"), "severity": "high"})

    # ------------------------------
    # 6. Unhealthy pods
    unhealthy = metrics.get("unhealthy_pods", [])
    for m in unhealthy:
        anomalies["unhealthy_pods"].append({"namespace": m.get("namespace"), "pod": m.get("pod"), "phase": m.get("phase"), "severity": "medium"})

    # ------------------------------
    # 7. Pending pods
    pending = metrics.get("pending_pods", [])
    for m in pending:
        anomalies["pending_pods"].append({"namespace": m.get("namespace"), "pod": m.get("pod"), "severity": "low"})

    # ------------------------------
    # 8. API errors
    api_errors = metrics.get("api_error_rate", [])
    for m in api_errors:
        if m.get("value") and m["value"] > 0.01:  # threshold: 1% error rate
            anomalies["api_errors"].append({"code": m.get("code"), "rate": m["value"], "severity": "medium"})

    # ------------------------------
    # 9. Log errors / warnings
    for line in logs.get("recent_errors", []):
        anomalies["log_errors"].append({"line": line, "severity": "medium"})
    for line in logs.get("recent_warnings", []):
        anomalies["log_warnings"].append({"line": line, "severity": "low"})

    # ------------------------------
    # 10. Tempo traces errors
    for trace in traces.get("error_traces", []):
        anomalies["traces_errors"].append({"trace_id": trace.get("traceID"), "severity": "medium"})

    # ------------------------------
    # Remove empty categories
    anomalies = {k: v for k, v in anomalies.items() if v}

    log.info("Detected anomalies: %s categories", len(anomalies))
    return anomalies