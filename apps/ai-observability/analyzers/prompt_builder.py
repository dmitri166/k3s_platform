"""Prompt builder for constructing RCA prompts."""

from typing import Any, Dict
import json


def build_rca_prompt(metrics: Dict[str, Any], logs: Dict[str, Any], traces: Dict[str, Any], events: Dict[str, Any], anomalies: Dict[str, Any], analysis_date: str) -> str:
    """Construct the prompt with cluster data for RCA."""
    metrics_json = json.dumps(metrics, indent=2, default=str)[:1000]
    logs_json = json.dumps(logs, indent=2, default=str)[:1000]
    traces_json = json.dumps(traces, indent=2, default=str)[:1000]
    events_json = json.dumps(events, indent=2, default=str)[:500]
    anomalies_json = json.dumps(anomalies, indent=2, default=str)

    data_summary = f"""
---
## DETECTED ANOMALIES
{anomalies_json}

---
## PROMETHEUS METRICS
{metrics_json}

---
## LOKI LOGS
{logs_json}

---
## TEMPO TRACES
{traces_json}

---
## KUBERNETES EVENTS
{events_json}

---
## YOUR TASK
Provide a comprehensive Root Cause Analysis report in Markdown with the following sections:

1. **Anomaly Summary** – List and describe detected anomalies.
2. **Root Cause Analysis** – Explain probable causes for each anomaly, correlating metrics, logs, traces, and events.
3. **Impact Assessment** – Describe potential impacts on the cluster.
4. **Recommendations** – Actionable steps to resolve issues, including kubectl/helm commands.
5. **Prevention Measures** – Suggestions to avoid future occurrences.

Be specific, concise, and actionable. Use Markdown tables and code blocks where helpful.
"""
