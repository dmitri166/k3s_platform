"""Entrypoint for AI Observability service."""

import asyncio
import logging
import time
from datetime import datetime, timezone

from collectors.prometheus import PrometheusCollector
from collectors.loki import LokiCollector
from collectors.tempo import TempoCollector
from collectors.kubernetes_api import KubernetesAPICollector
from analyzers.anomaly import detect_anomalies
from analyzers.prompt_builder import build_rca_prompt
from ai.groq_client import GroqClient
from reporters.markdown import generate_markdown_report, save_report
from reporters.grafana_annotator import annotate_grafana
from slack_bot import SlackBot
import config

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("ai-observability")

# Config with log
config_dict = config.config.model_dump()
config_dict['log'] = log

async def main_loop():
    """Main loop running every hour."""
    groq_client = GroqClient(config_dict)
    groq_client.initialize()

    slack_bot = SlackBot(config_dict)

    # Start Slack bot in background
    slack_task = asyncio.create_task(slack_bot.start())

    while True:
        analysis_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        log.info("Starting AI Observability analysis – %s", analysis_date)

        # Collect data
        prometheus_collector = PrometheusCollector(config_dict)
        loki_collector = LokiCollector(config_dict)
        tempo_collector = TempoCollector(config_dict)
        k8s_collector = KubernetesAPICollector(config_dict)

        metrics = prometheus_collector.collect()
        logs = loki_collector.collect()
        traces = tempo_collector.collect()
        events = k8s_collector.collect()

        # Detect anomalies
        anomalies = detect_anomalies(metrics, logs, traces, events)

        # If anomalies detected, analyze with LLM
        if anomalies:
            prompt = build_rca_prompt(metrics, logs, traces, events, anomalies, analysis_date)
            analysis = groq_client.analyze(prompt)

            # Generate report
            report_content = generate_markdown_report(analysis, metrics, logs, traces, events, anomalies, config_dict)

            # Save report
            raw_data = {
                "date": analysis_date,
                "metrics": metrics,
                "logs": logs,
                "traces": traces,
                "events": events,
                "anomalies": anomalies,
            }
            save_report(report_content, raw_data, config_dict)

            # Annotate Grafana
            annotate_grafana("AI Detected Anomalies", analysis[:200] + "...", ["ai", "anomaly"], config_dict)

            # Send to Slack
            await slack_bot.send_alert(f"Anomalies detected: {len(anomalies)} categories. Check RCA report.", report_content)

        else:
            log.info("No anomalies detected.")

        # Wait 1 hour
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main_loop())
