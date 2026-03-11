"""Slack SocketMode bot for alerts and ad-hoc queries."""

import asyncio
import json
import logging
from typing import Any, Dict

from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from ai.groq_client import GroqClient
from analyzers.prompt_builder import build_rca_prompt
from collectors.prometheus import PrometheusCollector


class SlackBot:
    """Slack bot using Socket Mode."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.web_client = WebClient(token=config["SLACK_BOT_TOKEN"])
        self.socket_client = SocketModeClient(
            app_token=config["SLACK_APP_TOKEN"], web_client=self.web_client
        )
        self.groq_client = GroqClient(config)
        self.groq_client.initialize()
        self.bot_user_id = config.get("BOT_USER_ID")
        if not self.bot_user_id:
            log = self.config.get("log", logging.getLogger(__name__))
            log.warning("BOT_USER_ID is not set. Mentions may not be stripped correctly.")

    async def start(self):
        """Start the Socket Mode client."""
        log = self.config.get("log", logging.getLogger(__name__))
        log.info("Starting Slack SocketMode bot...")

        # Register the async event handler
        self.socket_client.socket_mode_request_listeners.append(self.process)

        # Connect and keep the bot running
        await self.socket_client.connect()
        log.info("Slack SocketMode bot connected. Listening for messages...")
        await asyncio.Event().wait()  # keep alive

    async def process(self, client: SocketModeClient, req: SocketModeRequest):
        """Process incoming SocketMode events asynchronously."""
        if req.type == "events_api":
            # Acknowledge the request
            response = SocketModeResponse(envelope_id=req.envelope_id)
            await client.send_socket_mode_response(response)

            event = req.payload["event"]

            # Handle app mentions or direct messages
            if (
                event["type"] == "app_mention"
                or (
                    event["type"] == "message"
                    and event.get("channel_type") == "im"
                    and "bot_id" not in event
                )
            ):
                await self.handle_mention(event)

    async def handle_mention(self, event: Dict[str, Any]):
        """Handle @mention messages."""
        log = self.config.get("log", logging.getLogger(__name__))

        text = event.get("text", "")
        channel = event["channel"]
        user = event["user"]

        # Remove the bot mention
        message = text.replace(f"<@{self.bot_user_id}>", "").strip() if self.bot_user_id else text.strip()

        log.info("Received mention: '%s' from %s", message, user)

        # Determine response
        try:
            if "latency" in message.lower():
                collector = PrometheusCollector(self.config)
                metrics = collector.collect()
                prompt = f"Analyze latency issues: {json.dumps(metrics.get('api_latency_p99_seconds', []), indent=2)}"
                response_text = self.groq_client.analyze(prompt)
            else:
                response_text = (
                    "I'm sorry, I can help with latency or anomaly queries. "
                    "Mention me with 'latency' or 'anomaly'."
                )
        except Exception as exc:
            log.error("Error handling mention: %s", exc)
            response_text = "Sorry, I encountered an error while processing your request."

        # Send response
        try:
            await self.web_client.chat_postMessage(
                channel=channel, text=f"<@{user}> {response_text}"
            )
        except Exception as exc:
            log.error("Failed to send message to Slack: %s", exc)

    async def send_alert(self, message: str, report: str):
        """Send alert to Slack channel."""
        channel = self.config.get("SLACK_CHANNEL", "#alerts")
        log = self.config.get("log", logging.getLogger(__name__))

        try:
            # Send summary
            await self.web_client.chat_postMessage(channel=channel, text=message)
            # Send full report truncated to 4000 chars
            await self.web_client.chat_postMessage(channel=channel, text=f"Full RCA Report:\n{report[:4000]}")
            log.info("Alert sent to Slack channel %s", channel)
        except Exception as exc:
            log.error("Failed to send alert to Slack: %s", exc)