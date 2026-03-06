"""Anomaly detection engine using statistical methods."""

import numpy as np
import pandas as pd
from typing import Any, Dict, List
from collections import defaultdict


def detect_anomalies(metrics: Dict[str, Any], logs: Dict[str, Any], traces: Dict[str, Any], events: Dict[str, Any]) -> Dict[str, Any]:
    """Detect anomalies in metrics, logs, traces, and events."""
    anomalies = defaultdict(list)

    # CPU/Memory spikes
    for namespace_data in metrics.get("cpu_by_namespace", []):
        if float(namespace_data.get("value", 0)) > 1.0:  # Example threshold, adjust based on baseline
            anomalies["cpu_spikes"].append(namespace_data)

    for namespace_data in metrics.get("memory_by_namespace_mb", []):
        mb_val = float(namespace_data.get("value", "0 MB").split()[0])
        if mb_val > 1000:  # Example threshold
            anomalies["memory_spikes"].append(namespace_data)

    # API latency spikes
    for latency in metrics.get("api_latency_p99_seconds", []):
        if float(latency.get("value", 0)) > 1.0:  # Example threshold
            anomalies["latency_spikes"].append(latency)

    # Cross-reference errors with traces/events
    error_logs = logs.get("recent_errors", [])
    if error_logs:
        anomalies["log_errors"].extend(error_logs[:10])

    crash_events = events.get("recent_events", [])
    if crash_events:
        anomalies["crash_events"].extend(crash_events[:10])

    error_traces = traces.get("error_traces", [])
    if error_traces:
        anomalies["error_traces"].extend(error_traces[:10])

    return dict(anomalies)


def calculate_z_score(series: List[float]) -> List[float]:
    """Calculate Z-scores for a series."""
    if not series:
        return []
    mean = np.mean(series)
    std = np.std(series)
    if std == 0:
        return [0] * len(series)
    return [(x - mean) / std for x in series]


# Example usage for moving averages, but simplified
def moving_average_anomaly(data: List[float], window: int = 5) -> List[bool]:
    """Detect anomalies using moving average."""
    if len(data) < window:
        return [False] * len(data)
    anomalies = []
    for i in range(len(data)):
        start = max(0, i - window + 1)
        avg = np.mean(data[start:i+1])
        std = np.std(data[start:i+1])
        if std > 0 and abs(data[i] - avg) > 2 * std:
            anomalies.append(True)
        else:
            anomalies.append(False)
    return anomalies
