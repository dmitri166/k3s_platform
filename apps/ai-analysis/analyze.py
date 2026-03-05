#!/usr/bin/env python3
"""
analyze.py – K3s AI Analysis Pipeline

Collects Prometheus metrics and Loki logs from the cluster, sends them
to Groq for AI-powered analysis, and writes a daily Markdown
report to REPORT_DIR.

Run:
    python analyze.py
Environment variables (see config.py):
    GROQ_API_KEY, PROMETHEUS_URL, LOKI_URL, REPORT_DIR, LOOKBACK_HOURS
"""

import json
from typing import Any
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from groq import Groq

import config

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("ai-analysis")

# ── Rate-limit state ───────────────────────────────────────────────────────────
_groq_call_timestamps: list[float] = []

def _rate_limited_groq_call(client: Groq, prompt: str) -> str:
    """Send prompt to Groq, enforcing GROQ_MAX_RPM rate limit."""
    global _groq_call_timestamps
    now = time.monotonic()
    window = 60.0

    # Purge timestamps older than 60 s
    _groq_call_timestamps = [t for t in _groq_call_timestamps if now - t < window]

    if len(_groq_call_timestamps) >= config.GROQ_MAX_RPM:
        sleep_for = window - (now - _groq_call_timestamps[0]) + 0.5
        log.info("Rate limit reached – sleeping %.1fs", sleep_for)
        time.sleep(sleep_for)

    _groq_call_timestamps.append(time.monotonic())
    
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are an expert Site Reliability Engineer (SRE) and Kubernetes administrator. You write concise, production-grade Markdown reports.",
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or "No content returned from Groq."


# ── Prometheus helpers ─────────────────────────────────────────────────────────

def _prom_query(query: str) -> list[dict]:
    """Execute an instant PromQL query and return the result list."""
    url = f"{config.PROMETHEUS_URL}/api/v1/query"
    try:
        resp = requests.get(
            url,
            params={"query": query},
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        if data["status"] != "success":
            log.warning("Prometheus query '%s' returned non-success status: %s", query, data["status"])
            return []
        return data["data"]["result"]
    except Exception as exc:
        log.error("Prometheus query failed: %s – %s", query, exc)
        return []


def _prom_range_query(query: str, hours: int) -> list[dict]:
    """Execute a range PromQL query over the last N hours."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    url = f"{config.PROMETHEUS_URL}/api/v1/query_range"
    try:
        resp = requests.get(
            url,
            params={
                "query": query,
                "start": start.timestamp(),
                "end": end.timestamp(),
                "step": "5m",
            },
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        if data["status"] != "success":
            return []
        return data["data"]["result"]
    except Exception as exc:
        log.error("Prometheus range query failed: %s – %s", query, exc)
        return []


def collect_prometheus_metrics() -> dict:
    """Gather key cluster metrics from Prometheus."""
    log.info("Collecting Prometheus metrics …")

    hours = config.LOOKBACK_HOURS

    # --- Cluster-level resource usage ---
    cpu_usage = _prom_query(
        'sum(rate(container_cpu_usage_seconds_total{container!=""}[5m])) by (namespace)'
    )
    mem_usage = _prom_query(
        'sum(container_memory_working_set_bytes{container!=""}) by (namespace)'
    )
    node_cpu = _prom_query(
        '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
    )
    node_mem_pct = _prom_query(
        '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'
    )

    # --- Pod health ---
    pod_restarts = _prom_query(
        f'sum(increase(kube_pod_container_status_restarts_total[{hours}h])) by (namespace, pod) > 0'
    )
    pod_not_running = _prom_query(
        'kube_pod_status_phase{phase!~"Running|Succeeded"}'
    )

    # --- API server latency (P99) ---
    api_latency = _prom_query(
        'histogram_quantile(0.99, sum(rate(apiserver_request_duration_seconds_bucket[5m])) by (le, verb))'
    )

    # --- PVC usage ---
    pvc_usage = _prom_query(
        '(kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes) * 100'
    )

    def _simplify(result_list: list[dict], value_index: int = 1) -> list[dict]:
        """Convert Prometheus result to a compact list of dicts."""
        out: list[dict[str, Any]] = []
        for item in result_list:
            entry = dict(item.get("metric", {}))
            val = item.get("value", item.get("values", [[None, "N/A"]]))
            if isinstance(val, list) and val and isinstance(val[0], list):
                last_sample: list = val[-1]  # innermost sample pair [timestamp, value]
                entry["value"] = last_sample[value_index]
            elif isinstance(val, list) and len(val) == 2:
                entry["value"] = val[value_index]
            out.append(entry)
        return out[:20]  # type: ignore # cap to avoid oversized prompts

    return {
        "cpu_by_namespace":        _simplify(cpu_usage),
        "memory_by_namespace_mb":  [
            {**d, "value": f"{float(d['value'])/1024/1024:.1f} MB"}
            for d in _simplify(mem_usage)
        ],
        "node_cpu_pct":            _simplify(node_cpu),
        "node_memory_pct":         _simplify(node_mem_pct),
        "pod_restarts":            _simplify(pod_restarts),
        "unhealthy_pods":          _simplify(pod_not_running),
        "api_latency_p99_seconds": _simplify(api_latency),
        "pvc_usage_pct":           _simplify(pvc_usage),
    }


# ── Loki helpers ───────────────────────────────────────────────────────────────

def collect_loki_logs() -> dict:
    """Query Loki for error/warning patterns over the lookback window."""
    log.info("Collecting Loki logs …")

    end_ns   = int(datetime.now(timezone.utc).timestamp() * 1e9)
    start_ns = int((datetime.now(timezone.utc) - timedelta(hours=config.LOOKBACK_HOURS)).timestamp() * 1e9)

    def _loki_query(logql: str, limit: int = 50) -> list[str]:
        url = f"{config.LOKI_URL}/loki/api/v1/query_range"
        try:
            resp = requests.get(
                url,
                params={
                    "query": logql,
                    "start": start_ns,
                    "end": end_ns,
                    "limit": limit,
                    "direction": "backward",
                },
                timeout=config.HTTP_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
            lines: list[str] = []
            for stream in data.get("data", {}).get("result", []):
                for _ts, line in stream.get("values", []):
                    lines.append(line)
            return lines
        except Exception as exc:
            log.error("Loki query failed: %s – %s", logql, exc)
            return []

    errors   = _loki_query('{namespace=~".+"} |= "error" | line_format "{{.namespace}} {{.pod}} {{.line}}"', limit=100)
    warnings = _loki_query('{namespace=~".+"} |= "warning" | line_format "{{.namespace}} {{.pod}} {{.line}}"', limit=50)
    oom_logs = _loki_query('{namespace=~".+"} |= "OOMKilled"', limit=20)
    crash_logs = _loki_query('{namespace=~".+"} |~ "CrashLoopBackOff|BackOff"', limit=20)

    return {
        "recent_errors":   errors[:50],  # type: ignore
        "recent_warnings": warnings[:30],  # type: ignore
        "oom_events":      oom_logs,
        "crashloop_events": crash_logs,
    }


# ── AI analysis ────────────────────────────────────────────────────────────

def build_prompt(metrics: dict, logs: dict, analysis_date: str) -> str:
    """Construct the prompt with cluster data."""
    metrics_json = json.dumps(metrics, indent=2, default=str)
    logs_json    = json.dumps(logs,    indent=2, default=str)

    return f"""Analyse the following real-time data collected from a K3s Kubernetes cluster on {analysis_date}.

---
## PROMETHEUS METRICS (last {config.LOOKBACK_HOURS}h)
{metrics_json}

---
## LOKI LOG SAMPLES (last {config.LOOKBACK_HOURS}h)
{logs_json}

---
## YOUR TASK
Produce a structured cluster health report in Markdown with the following sections:

1. **Executive Summary** – 3-5 sentence overview of cluster health
2. **Resource Utilisation** – analyse CPU, memory, PVC usage; flag namespaces above 80%
3. **Pod Health Issues** – list restarting/unhealthy pods with probable root causes
4. **Log Anomalies** – summarise error/warning patterns and security concerns
5. **Top 5 Recommendations** – prioritised, actionable steps (include kubectl/helm commands where appropriate)
6. **Risk Assessment** – table with columns: Risk | Severity (Critical/High/Medium/Low) | Mitigation
7. **Trend Observations** – any concerning trends that need monitoring

Be specific, concise, and production-grade. Use Markdown tables and code blocks where helpful.
"""


def run_groq_analysis(client: Groq, prompt: str) -> str:
    """Send prompt to Groq and return the analysis text."""
    log.info("Sending data to Groq model '%s' …", config.GROQ_MODEL)
    try:
        return _rate_limited_groq_call(client, prompt)
    except Exception as exc:
        log.error("Groq API call failed: %s", exc)
        return f"⚠️ Groq analysis failed: {exc}"



# ── Report storage ─────────────────────────────────────────────────────────────

def save_report(analysis_text: str, metrics: dict, logs: dict, date_str: str) -> Path:
    """Write Markdown report and raw JSON data to REPORT_DIR."""
    report_dir = Path(config.REPORT_DIR)
    report_dir.mkdir(parents=True, exist_ok=True)

    md_path   = report_dir / f"{date_str}.md"
    json_path = report_dir / f"{date_str}.json"

    # Markdown report
    header = f"""# K3s Cluster AI Analysis Report
**Date:** {date_str}  
**Model:** {config.GROQ_MODEL}  
**Lookback:** {config.LOOKBACK_HOURS}h  
**Prometheus:** {config.PROMETHEUS_URL}  
**Loki:** {config.LOKI_URL}  

---

"""
    md_path.write_text(header + analysis_text, encoding="utf-8")
    log.info("Markdown report saved → %s", md_path)

    # Raw JSON (metrics + logs for debugging/archiving)
    raw = {"date": date_str, "metrics": metrics, "logs": logs}
    json_path.write_text(json.dumps(raw, indent=2, default=str), encoding="utf-8")
    log.info("Raw JSON saved → %s", json_path)

    return md_path


def purge_old_reports() -> None:
    """Delete reports older than REPORT_RETENTION_DAYS."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.REPORT_RETENTION_DAYS)
    report_dir = Path(config.REPORT_DIR)
    if not report_dir.exists():
        return
    for f in report_dir.iterdir():
        if f.is_file():
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                f.unlink()
                log.info("Purged old report: %s", f.name)


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    analysis_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log.info("=== K3s AI Analysis starting – %s ===", analysis_date)

    # Configure Groq
    try:
        client = Groq(api_key=config.GROQ_API_KEY)
    except Exception as exc:
        log.error("Failed to initialize Groq client: %s", exc)
        client = None

    # 1. Collect data
    metrics = collect_prometheus_metrics()
    logs    = collect_loki_logs()

    # 2. Build prompt & analyse
    prompt   = build_prompt(metrics, logs, analysis_date)
    
    if client:
        analysis = run_groq_analysis(client, prompt)
    else:
        analysis = "⚠️ Groq client failed to initialize. See logs."

    # 3. Save report
    report_path = save_report(analysis, metrics, logs, analysis_date)

    # 4. Housekeeping
    purge_old_reports()

    log.info("=== Analysis complete → %s ===", report_path)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log.critical("Fatal error: %s", exc, exc_info=True)
        sys.exit(1)
