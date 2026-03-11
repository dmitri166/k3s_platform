"""Build RCA prompt for LLM including metrics/logs/traces/events per resource."""

import json
from typing import Dict, Any

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
{json.dumps(anomalies, indent=2)}

## METRICS
{json.dumps(metrics, indent=2)}

## LOGS
{json.dumps(logs, indent=2)}

## TRACES
{json.dumps(traces, indent=2)}

## EVENTS
{json.dumps(events, indent=2)}

## TASK
Provide a resource-level Root Cause Analysis report in Markdown:
- Include exact affected resources (pods, nodes, deployments, daemonsets, statefulsets, services, ingress, configmaps)
- Include metrics, logs, traces, and events
- Provide remediation commands (kubectl/helm) for each affected resource
- Be concise and actionable
"""
    return prompt