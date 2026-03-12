"""Async Slack SocketMode bot for AI observability queries."""

import os
import json
import logging
import asyncio
from typing import Dict, Any

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from ai.groq_client import GroqClient


class SlackBot:
    """Async Slack bot with full resource-level RCA."""

    RESOURCE_TYPES = ["pod", "node", "namespace", "deployment",
                      "statefulset", "daemonset", "service",
                      "ingress", "configmap"]

    def __init__(self, config):
        self.config = config
        self.web_client = AsyncWebClient(token=config.SLACK_BOT_TOKEN)
        self.socket_client = SocketModeClient(
            app_token=config.SLACK_APP_TOKEN,
            web_client=self.web_client,
        )
        self.groq_client = GroqClient(config)
        self.groq_client.initialize()

        self.bot_user_id = config.BOT_USER_ID or os.getenv("BOT_USER_ID", "")
        if not self.bot_user_id:
            logging.warning("BOT_USER_ID not set; mentions may not be stripped correctly.")

        self.resource_data: Dict[str, Any] = {}

    def update_resource_data(self, resource_data: Dict[str, Any]):
        self.resource_data = resource_data

    async def start(self):
        self.config.log.info("Starting Slack SocketMode bot...")
        self.socket_client.socket_mode_request_listeners.append(self.process)
        await self.socket_client.connect()

    async def process(self, client: SocketModeClient, req: SocketModeRequest):
        if req.type == "events_api":
            await client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))
            event = req.payload.get("event", {})
            if event.get("type") in ["app_mention", "message"]:
                if event.get("channel_type") == "im" or event.get("type") == "app_mention":
                    asyncio.create_task(self.handle_mention(event))

    async def handle_mention(self, event: Dict[str, Any]):
        text = event.get("text", "")
        channel = event.get("channel")
        user = event.get("user")
        if self.bot_user_id:
            text = text.replace(f"<@{self.bot_user_id}>", "").strip()

        self.config.log.info("Received mention: %s from %s", text, user)

        response = "I couldn't find the requested resource. Ask like: 'Why did pod <name> fail?'"

        for rtype in self.RESOURCE_TYPES:
            if rtype in text.lower():
                words = text.split()
                for i, word in enumerate(words):
                    if word.lower() == rtype and i + 1 < len(words):
                        resource_name = words[i + 1]
                        resource_info = self.resource_data.get(rtype, {}).get(resource_name)
                        if resource_info:
                            prompt = f"""
You are an AI Kubernetes observability assistant.
Resource Type: {rtype}
Resource Name: {resource_name}

Collected data for this resource:
Metrics: {json.dumps(resource_info.get('metrics', {}), indent=2)}
Logs: {json.dumps(resource_info.get('logs', [])[-50:], indent=2)}
Events: {json.dumps(resource_info.get('events', [])[-50:], indent=2)}
Traces: {json.dumps(resource_info.get('traces', []), indent=2)}

Question: {text}
Provide the exact root cause, errors, and remediation commands.
"""
                            response = self.groq_client.analyze(prompt)
                        else:
                            response = f"No data available for {rtype} '{resource_name}'."

        await self.web_client.chat_postMessage(channel=channel, text=f"<@{user}> {response}")

    async def send_alert(self, message: str, report: str):
        channel = self.config.SLACK_CHANNEL
        try:
            await self.web_client.chat_postMessage(channel=channel, text=message)
            await self.web_client.chat_postMessage(channel=channel, text=f"Full RCA Report:\n{report[:4000]}")
        except Exception as e:
            logging.error("Failed to send alert to Slack: %s", e)