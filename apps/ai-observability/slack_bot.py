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
        text = event.get("text", "").strip().lower()
        channel = event.get("channel")
        user = event.get("user")

        # Ignore messages from the bot itself to prevent infinite loops
        if user == self.bot_user_id:
            return

        # Ignore messages that appear to be the bot's own responses to prevent loops
        bot_response_patterns = [
            "i couldn't find the requested resource",
            "no data available for",
            "ask like:",
            "@k3s_platform_observility"  # The bot's handle
        ]
        if any(pattern in text for pattern in bot_response_patterns):
            return

        if self.bot_user_id:
            original_text = event.get("text", "")
            text = original_text.replace(f"<@{self.bot_user_id}>", "").strip().lower()

        self.config.log.info("Received mention: %s from %s", text, user)

        response = "I couldn't find the requested resource. Ask like: 'Why did pod <name> fail?' or 'Why are nodes failing?'"

        # Check for specific resource queries: "why did [resource] [name] fail"
        for rtype in self.RESOURCE_TYPES:
            if f"why" in text and rtype in text and "fail" in text:
                words = text.split()
                try:
                    rtype_index = words.index(rtype)
                    if rtype_index + 1 < len(words):
                        resource_name = words[rtype_index + 1].strip('\'"<>')
                        # Skip placeholders
                        if resource_name not in ['<name>', 'name', 'failing', 'fail']:
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

Question: {original_text}
Provide the exact root cause, errors, and remediation commands.
"""
                                response = self.groq_client.analyze(prompt)
                            else:
                                response = f"No data available for {rtype} '{resource_name}'."
                            break
                except ValueError:
                    pass

        # Check for general resource type queries: "why are [resource]s failing"
        if response.startswith("I couldn't"):
            for rtype in self.RESOURCE_TYPES:
                if f"why" in text and (rtype + "s" in text or rtype in text) and ("fail" in text or "failing" in text):
                    # Provide general analysis for this resource type
                    all_resources = self.resource_data.get(rtype, {})
                    if all_resources:
                        summary_data = {
                            "total_resources": len(all_resources),
                            "sample_metrics": {},
                            "sample_logs": [],
                            "sample_events": []
                        }
                        # Take samples from a few resources
                        for name, info in list(all_resources.items())[:3]:
                            summary_data["sample_metrics"][name] = info.get("metrics", {})
                            summary_data["sample_logs"].extend(info.get("logs", [])[:10])
                            summary_data["sample_events"].extend(info.get("events", [])[:10])

                        prompt = f"""
You are an AI Kubernetes observability assistant.

General analysis for {rtype} failures:

Summary data across all {rtype}s:
Total {rtype}s: {summary_data['total_resources']}

Sample metrics: {json.dumps(summary_data['sample_metrics'], indent=2)}
Sample logs: {json.dumps(summary_data['sample_logs'][-50:], indent=2)}
Sample events: {json.dumps(summary_data['sample_events'][-50:], indent=2)}

Question: {original_text}
Provide general insights about why {rtype}s might be failing and remediation suggestions.
"""
                        response = self.groq_client.analyze(prompt)
                    else:
                        response = f"No {rtype} data available for analysis."
                    break

        await self.web_client.chat_postMessage(channel=channel, text=f"<@{user}> {response}")

    async def send_alert(self, message: str, report: str):
        channel = self.config.SLACK_CHANNEL
        try:
            await self.web_client.chat_postMessage(channel=channel, text=message)
            await self.web_client.chat_postMessage(channel=channel, text=f"Full RCA Report:\n{report[:4000]}")
        except Exception as e:
            logging.error("Failed to send alert to Slack: %s", e)