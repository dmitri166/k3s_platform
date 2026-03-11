from typing import Dict, Any

def detect_anomalies(metrics: Dict[str, Any], logs: Dict[str, Any], traces: Dict[str, Any], events: Dict[str, Any]) -> Dict[str, Any]:
    anomalies = {}

    high_mem = [{"node": n.get("node"), "usage_pct": n.get("value")} for n in metrics.get("node_memory_pct", []) if n.get("value",0) > 85]
    if high_mem: anomalies["high_node_memory"] = high_mem

    restart_spikes = [{"namespace": p.get("namespace"), "pod": p.get("pod"), "restarts": p.get("value")} for p in metrics.get("pod_restart_spikes", []) if p.get("value",0) > 3]
    if restart_spikes: anomalies["pod_restart_spikes"] = restart_spikes

    if logs.get("oom"):
        anomalies["oom_pods"] = [{"namespace": l.get("namespace"), "pod": l.get("pod")} for l in logs["oom"]]
    if logs.get("crashloop"):
        anomalies["crashloop_pods"] = [{"namespace": l.get("namespace"), "pod": l.get("pod")} for l in logs["crashloop"]]

    if metrics.get("pending_pods"):
        anomalies["pending_pods"] = [{"namespace": p.get("namespace"), "pod": p.get("pod")} for p in metrics["pending_pods"]]

    if events.get("k8s_events"):
        anomalies["k8s_events"] = events["k8s_events"][:50]

    if traces.get("error_traces"):
        anomalies["traces"] = traces["error_traces"]

    return anomalies