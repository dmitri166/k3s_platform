import os
import json
import asyncio
import logging
from typing import Dict, Any

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from ai.groq_client import GroqClient
from collectors.prometheus import PrometheusCollector

class SlackBot:
    """Async Slack bot for AI observability."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.web_client = AsyncWebClient(token=config["SLACK_BOT_TOKEN"])
        self.socket_client = SocketModeClient(app_token=config["SLACK_APP_TOKEN"], web_client=self.web_client)
        self.groq_client = GroqClient(config)
        self.groq_client.initialize()
        self.bot_user_id = config.get("BOT_USER_ID") or os.getenv("BOT_USER_ID", "")
        if not self.bot_user_id:
            logging.warning("BOT_USER_ID is not set. Mentions may not be stripped correctly.")

    async def start(self):
        log = self.config.get("log", logging.getLogger(__name__))
        log.info("Starting Slack SocketMode bot…")
        self.socket_client.socket_mode_request_listeners.append(self.process)
        await self.socket_client.connect()

    async def process(self, client: SocketModeClient, req: SocketModeRequest):
        if req.type == "events_api":
            await client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))
            event = req.payload.get("event", {})
            if event.get("type") in ("app_mention", "message") and event.get("channel_type") == "im" and "bot_id" not in event:
                asyncio.create_task(self.handle_mention(event))

    async def handle_mention(self, event: Dict[str, Any]):
        text = event.get("text", "")
        channel = event.get("channel")
        user = event.get("user")

        if self.bot_user_id:
            text = text.replace(f"<@{self.bot_user_id}>", "").strip()

        log = self.config.get("log", logging.getLogger(__name__))
        log.info("Received mention: '%s' from %s", text, user)

        response = "I'm sorry, I can help with latency or anomaly queries. Mention me with 'latency' or 'anomaly'."
        if "latency" in text.lower():
            collector = PrometheusCollector(self.config)
            metrics = collector.collect()
            prompt = f"Analyze latency issues: {json.dumps(metrics.get('api_latency_p99', []), indent=2)}"
            response = self.groq_client.analyze(prompt)

        await self.web_client.chat_postMessage(channel=channel, text=f"<@{user}> {response}")

    async def send_alert(self, message: str, report: str):
        channel = self.config.get("SLACK_CHANNEL", "#alerts")
        log = self.config.get("log", logging.getLogger(__name__))
        try:
            await self.web_client.chat_postMessage(channel=channel, text=message)
            await self.web_client.chat_postMessage(channel=channel, text=f"Full RCA Report:\n{report[:4000]}")
            log.info("Alert sent to Slack channel %s", channel)
        except Exception as e:
            log.error("Failed to send Slack alert: %s", e)