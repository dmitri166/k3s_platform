"""Slack SocketMode bot for alerts and ad-hoc queries."""

import asyncio
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from typing import Any, Dict
import logging

from ai.groq_client import GroqClient
from analyzers.prompt_builder import build_rca_prompt


class SlackBot:
    """Slack bot using Socket Mode."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.web_client = WebClient(token=config['SLACK_BOT_TOKEN'])
        self.socket_client = SocketModeClient(
            app_token=config['SLACK_APP_TOKEN'],
            web_client=self.web_client
        )
        self.groq_client = GroqClient(config)
        self.groq_client.initialize()

    async def start(self):
        """Start the Socket Mode client."""
        log = self.config.get('log', logging.getLogger(__name__))
        log.info("Starting Slack SocketMode bot...")

        # Register event handler
        self.socket_client.socket_mode_request_listener = self.process

        # Establish connection
        await self.socket_client.connect()

    def process(self, client: SocketModeClient, req: SocketModeRequest):
        """Process incoming events."""
        if req.type == "events_api":
            # Acknowledge the request
            response = SocketModeResponse(envelope_id=req.envelope_id)
            client.send_socket_mode_response(response)

            # Process the event
            event = req.payload["event"]
            if event["type"] == "app_mention":
                asyncio.create_task(self.handle_mention(event))

    async def handle_mention(self, event: Dict[str, Any]):
        """Handle @mention messages."""
        text = event["text"]
        channel = event["channel"]
        user = event["user"]

        # Remove the mention
        message = text.replace(f"<@{self.config.get('BOT_USER_ID', '')}>", "").strip()

        log = self.config.get('log', logging.getLogger(__name__))
        log.info("Received mention: %s from %s", message, user)

        # For ad-hoc queries, collect data and analyze
        # Simplified: assume query like "Why is latency high?"
        if "latency" in message.lower():
            # Collect metrics
            from collectors.prometheus import PrometheusCollector
            collector = PrometheusCollector(self.config)
            metrics = collector.collect()

            prompt = f"Analyze latency issues: {json.dumps(metrics.get('api_latency_p99_seconds', []), indent=2)}"
            response = self.groq_client.analyze(prompt)
        else:
            response = "I'm sorry, I can help with latency or anomaly queries. Mention me with 'latency' or 'anomaly'."

        # Send response
        self.web_client.chat_postMessage(
            channel=channel,
            text=f"<@{user}> {response}"
        )

    async def send_alert(self, message: str, report: str):
        """Send alert to Slack channel."""
        channel = self.config.get('SLACK_CHANNEL', '#alerts')

        # Send summary
        self.web_client.chat_postMessage(
            channel=channel,
            text=message
        )

        # Optionally send full report if short
        if len(report) < 3000:
            self.web_client.chat_postMessage(
                channel=channel,
                text=f"Full RCA Report:\n{report}"
            )
