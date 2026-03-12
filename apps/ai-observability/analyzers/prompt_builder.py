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

    prompt = f"""
# Kubernetes Observability RCA
**Analysis Date:** {analysis_date}

## DETECTED ANOMALIES
{json.dumps(anomalies, indent=2, cls=DateTimeEncoder)}

## METRICS
{json.dumps(metrics, indent=2, cls=DateTimeEncoder)}

## LOGS
{json.dumps(logs, indent=2, cls=DateTimeEncoder)}

## TRACES
{json.dumps(traces, indent=2, cls=DateTimeEncoder)}

## EVENTS
{json.dumps(events, indent=2, cls=DateTimeEncoder)}

## TASK
Provide a resource-level Root Cause Analysis report in Markdown:
- Include exact affected resources (pods, nodes, deployments, daemonsets, statefulsets, services, ingress, configmaps)
- Include metrics, logs, traces, and events
- Provide remediation commands (kubectl/helm) for each affected resource
- Be concise and actionable
"""
    return prompt