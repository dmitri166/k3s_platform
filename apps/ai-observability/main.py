"""Entrypoint for AI Observability service."""

import asyncio
import logging
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
from config import Config

# Logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ai-observability")

config = Config()
config.log = log

async def main_loop():
    groq_client = GroqClient(config)
    groq_client.initialize()
    slack_bot = SlackBot(config)
    await slack_bot.start()

    while True:
        analysis_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        config.log.info("Starting AI Observability analysis – %s", analysis_date)

        prometheus_collector = PrometheusCollector(config)
        loki_collector = LokiCollector(config)
        tempo_collector = TempoCollector(config)
        k8s_collector = KubernetesAPICollector(config)

        # Collect all data
        metrics = prometheus_collector.collect()
        logs = loki_collector.collect()
        traces = tempo_collector.collect()
        events, resource_data = k8s_collector.collect()

        # Merge metrics/logs/traces/events per resource (already done in collect)
        # attach metrics per resource type
        for rtype, rmetrics in metrics.items():
            for rname, mdata in rmetrics.items():
                if rname in resource_data.get(rtype, {}):
                    resource_data[rtype][rname]["metrics"] = mdata

        slack_bot.update_resource_data(resource_data)

        anomalies = detect_anomalies(metrics, logs, traces, {"k8s_events": events})
        if anomalies:
            prompt = build_rca_prompt(metrics, logs, traces, events, anomalies, analysis_date)
            analysis = groq_client.analyze(prompt)
            report_content = generate_markdown_report(analysis, metrics, logs, traces, events, anomalies, config_dict)
            save_report(report_content, {
                "date": analysis_date,
                "metrics": metrics,
                "logs": logs,
                "traces": traces,
                "events": events,
                "anomalies": anomalies
            }, config_dict)
            annotate_grafana("AI Detected Anomalies", analysis[:200]+"...", ["ai","anomaly"], config_dict)
            await slack_bot.send_alert(f"Anomalies detected: {len(anomalies)} categories.", report_content)
        else:
            log.info("No anomalies detected.")

        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main_loop())