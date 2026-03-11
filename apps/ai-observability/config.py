"""Configuration loading using Pydantic."""

from pydantic_settings import BaseSettings
import os


class Config(BaseSettings):
    """Configuration for AI Observability service."""
    
    LOG_LEVEL: str = "INFO"
    
    # API Keys
    GROQ_API_KEY: str = ""
    SLACK_APP_TOKEN: str = ""
    SLACK_BOT_TOKEN: str = ""
    GRAFANA_API_KEY: str = ""

    # URLs
    PROMETHEUS_URL: str = "http://kube-prometheus-stack-prometheus.monitoring.svc:9090"
    LOKI_URL: str = "http://loki-stack.monitoring.svc.cluster.local:3100/loki/api/v1/push"
    # TEMPO_URL: str = "http://tempo.monitoring.svc.cluster.local:3100/api/traces/search"
    GRAFANA_URL: str = "http://kube-prometheus-stack-grafana.monitoring.svc:80"

    # Parameters
    LOOKBACK_HOURS: int = 24
    HTTP_TIMEOUT_SECONDS: int = 30
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GROQ_MAX_RPM: int = 30
    REPORT_DIR: str = "/reports"

    # Slack
    SLACK_CHANNEL: str = "#alerts"

    class Config:
        env_file = ".env"
        case_sensitive = False


config = Config()
