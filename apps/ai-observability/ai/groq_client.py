"""Groq API client for AI analysis."""

from groq import Groq
from typing import Any, Dict
import time
import logging


class GroqClient:
    """Client for interacting with Groq API."""

    def __init__(self, config):
        self.config = config
        self.client = None
        self._call_timestamps: list[float] = []

    def initialize(self):
        """Initialize the Groq client."""
        try:
            self.client = Groq(api_key=self.config.GROQ_API_KEY)
            self.config.log.info("Groq client initialized.")
        except Exception as exc:
            self.config.log.error("Failed to initialize Groq client: %s", exc)

    def analyze(self, prompt: str) -> str:
        """Send prompt to Groq and return analysis."""
        if not self.client:
            return "Groq client not initialized."

        self._rate_limit()
        self.config.log.info("Sending prompt to Groq model '%s' …", self.config.GROQ_MODEL)

        # Fix: Ensure prompt is never None or empty
        safe_prompt = str(prompt) if prompt else "No data available for analysis."

        try:
            response = self.client.chat.completions.create(
                model=self.config.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Site Reliability Engineer (SRE) and Kubernetes administrator. Provide concise, production-grade analysis.",
                    },
                    {
                        "role": "user",
                        "content": safe_prompt,  # guaranteed non-null
                    }
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content or "No content returned from Groq."
        except Exception as exc:
            self.config.log.error("Groq API call failed: %s", exc)
            return f"Groq analysis failed: {exc}"

    def _rate_limit(self):
        """Enforce rate limiting."""
        now = time.monotonic()
        window = 60.0
        max_calls = self.config.GROQ_MAX_RPM

        self._call_timestamps = [t for t in self._call_timestamps if now - t < window]

        if len(self._call_timestamps) >= max_calls:
            sleep_for = window - (now - self._call_timestamps[0]) + 0.5
            self.config.log.info("Rate limit reached – sleeping %.1fs", sleep_for)
            time.sleep(sleep_for)

        self._call_timestamps.append(time.monotonic())
