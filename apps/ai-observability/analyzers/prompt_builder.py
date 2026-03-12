"""Build RCA prompt for LLM including metrics/logs/traces/events per resource."""

import json
from datetime import datetime, date
from typing import Dict, Any

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

def build_rca_prompt(metrics: Dict[str, Any],
                     logs: Dict[str, Any],
                     traces: Dict[str, Any],
                     events: Dict[str, Any],
                     anomalies: Dict[str, Any],
                     analysis_date: str) -> str:

    # Truncate data to prevent token limits - keep only essential information
    def truncate_data(data: Dict[str, Any], max_items: int = 10) -> Dict[str, Any]:
        """Truncate dictionary data to prevent token limit issues."""
        if not isinstance(data, dict):
            return data
        truncated = {}
        for key, value in data.items():
            if isinstance(value, list):
                truncated[key] = value[:max_items]  # Keep only first N items
            elif isinstance(value, dict):
                truncated[key] = truncate_data(value, max_items)
            else:
                truncated[key] = value
        return truncated

    # Truncate large datasets extremely aggressively
    truncated_metrics = truncate_data(metrics, 1)
    truncated_logs = truncate_data(logs, 1)
    truncated_traces = truncate_data(traces, 1)
    truncated_events = events[:2] if isinstance(events, list) else truncate_data({"events": events}, 1).get("events", events)
    truncated_anomalies = truncate_data(anomalies, 1)

    prompt = f"""
# Kubernetes Observability RCA
**Analysis Date:** {analysis_date}

## DETECTED ANOMALIES
{json.dumps(truncated_anomalies, indent=2, cls=DateTimeEncoder)}

## METRICS
{json.dumps(truncated_metrics, indent=2, cls=DateTimeEncoder)}

## LOGS
{json.dumps(truncated_logs, indent=2, cls=DateTimeEncoder)}

## TRACES
{json.dumps(truncated_traces, indent=2, cls=DateTimeEncoder)}

## EVENTS
{json.dumps(truncated_events, indent=2, cls=DateTimeEncoder)}

## TASK
Provide a resource-level Root Cause Analysis report in Markdown:
- Include exact affected resources (pods, nodes, deployments, daemonsets, statefulsets, services, ingress, configmaps)
- Include metrics, logs, traces, and events
- Provide remediation commands (kubectl/helm) for each affected resource
- Be concise and actionable
"""
    return prompt