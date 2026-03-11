"""Slack bot for AI Observability using synchronous Slack WebClient."""

import json
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from typing import Any, Dict

from ai.groq_client import GroqClient
from analyzers.prompt_builder import build_rca_prompt  # Your existing prompt builder
from collectors.prometheus import PrometheusCollector


class SlackBot:
    """Synchronous Slack bot for alerts and ad-hoc queries."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.web_client = WebClient(token=config['SLACK_BOT_TOKEN'])
        self.groq_client = GroqClient(config)
        self.groq_client.initialize()
        self.bot_user_id = config.get('BOT_USER_ID', '')

        if not self.bot_user_id:
            logging.warning("BOT_USER_ID is not set. Mentions may not be stripped correctly.")

    def process_message(self, event: Dict[str, Any]):
        """Process incoming Slack event message."""
        if "bot_id" in event:
            return  # Ignore messages from other bots

        text = event.get("text", "")
        channel = event.get("channel")
        user = event.get("user")

        if not text or not channel or not user:
            return

        # Remove bot mention if present
        if self.bot_user_id:
            text = text.replace(f"<@{self.bot_user_id}>", "").strip()

        logging.info("Received message: '%s' from user %s", text, user)

        # Handle ad-hoc queries
        response_text = self.handle_query(text)

        # Send response
        self.send_message(channel, f"<@{user}> {response_text}")

    def handle_query(self, message: str) -> str:
        """Handle user queries and send to Groq if relevant."""
        if "latency" in message.lower():
            collector = PrometheusCollector(self.config)
            metrics = collector.collect()
            prompt = f"Analyze latency issues: {json.dumps(metrics.get('api_latency_p99_seconds', []), indent=2)}"
            return self.groq_client.analyze(prompt)

        elif "anomaly" in message.lower():
            # Could build a custom prompt for anomalies
            prompt = "Analyze anomalies in the cluster over the last 24h"
            return self.groq_client.analyze(prompt)

        else:
            return "I'm sorry, I can help with 'latency' or 'anomaly' queries. Please mention me with one of those keywords."

    def send_message(self, channel: str, text: str):
        """Send a message to Slack channel."""
        try:
            # Truncate to 4000 chars
            truncated_text = text[:4000]
            self.web_client.chat_postMessage(channel=channel, text=truncated_text)
            logging.info("Sent message to Slack channel %s", channel)
        except SlackApiError as e:
            logging.error("Failed to send message to Slack: %s", e.response['error'])

    def send_alert(self, message: str, report: str):
        """Send alert + full RCA report to Slack."""
        channel = self.config.get("SLACK_CHANNEL", "#alerts")
        self.send_message(channel, message)
        self.send_message(channel, f"Full RCA Report:\n{report[:4000]}")
        