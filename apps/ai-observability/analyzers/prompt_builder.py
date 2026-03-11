from typing import Dict, Any
import json

def build_rca_prompt(metrics: Dict[str, Any], logs: Dict[str, Any], traces: Dict[str, Any], events: Dict[str, Any], anomalies: Any, analysis_date: str) -> str:
    """Build RCA prompt for LLM."""
    prompt = f"""
Date: {analysis_date}

Detected anomalies:
{json.dumps(anomalies, indent=2)}

Metrics:
{json.dumps(metrics, indent=2)[:2000]}

Logs:
{json.dumps(logs, indent=2)[:2000]}

Traces:
{json.dumps(traces, indent=2)[:2000]}

Kubernetes events:
{json.dumps(events, indent=2)[:1000]}

Task:
Provide a concise root cause analysis, affected components, severity, and actionable remediation steps. Use Markdown tables and code blocks where helpful.
"""
    return prompt