"""Slack SocketMode bot for AI Observability alerts and queries."""

import asyncio
import json
import logging
from typing import Any, Dict

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from ai.groq_client import GroqClient
from collectors.prometheus import PrometheusCollector
from collectors.loki import LokiCollector
from analyzers.prompt_builder import build_rca_prompt


class SlackBot:
    """Slack bot using Socket Mode (async)."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Async Slack client
        self.web_client = AsyncWebClient(token=config['SLACK_BOT_TOKEN'])
        self.socket_client = SocketModeClient(
            app_token=config['SLACK_APP_TOKEN'],
            web_client=self.web_client
        )

        # Groq client
        self.groq_client = GroqClient(config)
        self.groq_client.initialize()

    async def start(self):
        """Start the Slack SocketMode client."""
        log = self.config.get('log', logging.getLogger(__name__))
        log.info("Starting Slack SocketMode bot...")

        # Register async listener
        self.socket_client.socket_mode_request_listeners.append(self.process)

        # Connect
        await self.socket_client.connect()

    async def process(self, client: SocketModeClient, req: SocketModeRequest):
        """Process incoming events asynchronously."""
        if req.type == "events_api":
            # Acknowledge event
            response = SocketModeResponse(envelope_id=req.envelope_id)
            await client.send_socket_mode_response(response)

            # Handle events
            event = req.payload.get("event", {})
            if event.get("type") == "app_mention":
                await self.handle_mention(event)
            elif event.get("type") == "message" and event.get("channel_type") == "im" and "bot_id" not in event:
                await self.handle_mention(event)

    async def handle_mention(self, event: Dict[str, Any]):
        """Handle messages directed at the bot."""
        text = event.get("text", "")
        channel = event.get("channel")
        user = event.get("user")

        if not text or not channel or not user:
            return  # Ignore invalid events

        # Strip bot mention
        bot_id = self.config.get("BOT_USER_ID", "")
        message = text.replace(f"<@{bot_id}>", "").strip()

        log = self.config.get('log', logging.getLogger(__name__))
        log.info("Received mention: %s from %s", message, user)

        if not message:
            # Empty message after stripping mention
            await self.send_message(channel, f"<@{user}> Please provide a query.")
            return

        # Example: respond to "latency" or "anomaly" queries
        if "latency" in message.lower() or "anomaly" in message.lower():
            # Collect metrics from Prometheus and Loki
            prometheus = PrometheusCollector(self.config)
            loki = LokiCollector(self.config)

            prometheus_data = prometheus.collect()
            loki_data = loki.collect()

            # Build a prompt for Groq
            prompt = build_rca_prompt(prometheus_data, loki_data, message)

            # Analyze via Groq
            response = self.groq_client.analyze(prompt)
        else:
            response = (
                "I'm sorry, I can help with 'latency' or 'anomaly' queries. "
                "Please mention me with one of those keywords."
            )

        await self.send_message(channel, f"<@{user}> {response}")

    async def send_message(self, channel: str, text: str):
        """Send a message to Slack channel asynchronously."""
        try:
            await self.web_client.chat_postMessage(channel=channel, text=text)
        except Exception as exc:
            log = self.config.get('log', logging.getLogger(__name__))
            log.error("Failed to send message to Slack: %s", exc)

    async def send_alert(self, message: str, report: str):
        """Send alert + full RCA report to configured Slack channel."""
        channel = self.config.get("SLACK_CHANNEL", "#alerts")

        await self.send_message(channel, message)
        await self.send_message(channel, f"Full RCA Report:\n{report[:4000]}")