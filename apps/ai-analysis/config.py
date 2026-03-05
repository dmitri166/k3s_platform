"""
config.py – Central configuration for AI analysis pipeline.
All values are read from environment variables with safe defaults.
"""

import os

# ── Observability endpoints ────────────────────────────────────────────────────
PROMETHEUS_URL: str = os.getenv(
    "PROMETHEUS_URL",
    "http://kube-prometheus-stack-prometheus.monitoring.svc:9090",
)
LOKI_URL: str = os.getenv(
    "LOKI_URL",
    "http://loki.monitoring.svc:3100",
)

# ── Groq AI ──────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.environ["GROQ_API_KEY"]          # required – fail fast
GROQ_MODEL: str   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Requests per minute ceiling to stay within free-tier limits (30 rpm for Groq typically).
# We use 10 as a safe conservative default so a single run never spikes.
GROQ_MAX_RPM: int = int(os.getenv("GROQ_MAX_RPM", "10"))

# ── Report storage ─────────────────────────────────────────────────────────────
REPORT_DIR: str       = os.getenv("REPORT_DIR", "/reports")
REPORT_RETENTION_DAYS: int = int(os.getenv("REPORT_RETENTION_DAYS", "30"))

# ── Query window ───────────────────────────────────────────────────────────────
# How many hours of data to pull in each analysis run.
LOOKBACK_HOURS: int = int(os.getenv("LOOKBACK_HOURS", "24"))

# ── Timeouts ───────────────────────────────────────────────────────────────────
HTTP_TIMEOUT_SECONDS: int = int(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))
