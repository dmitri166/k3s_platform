import asyncio
import logging
from datetime import datetime, timezone

from config import Config
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

config = Config()
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("ai-observability")

config_dict = config.model_dump()
config_dict['log'] = log

async def main_loop():
    groq_client = GroqClient(config_dict)
    groq_client.initialize()
    slack_bot = SlackBot(config_dict)
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

        anomalies = detect_anomalies(metrics, logs, traces, events)

        if anomalies:
            prompt = build_rca_prompt(metrics, logs, traces, events, anomalies, analysis_date)
            analysis = groq_client.analyze(prompt)

            report_content = generate_markdown_report(analysis, metrics, logs, traces, events, anomalies, config_dict)
            save_report(report_content, {"date": analysis_date, "metrics": metrics, "logs": logs, "traces": traces, "events": events, "anomalies": anomalies}, config_dict)

            annotate_grafana("AI Detected Anomalies", analysis[:200]+"...", ["ai","anomaly"], config_dict)
            await slack_bot.send_alert(f"Anomalies detected: {len(anomalies)} categories. Check RCA report.", report_content)
        else:
            log.info("No anomalies detected.")

        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main_loop())