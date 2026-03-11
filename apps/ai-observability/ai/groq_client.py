"""Groq API client for AI analysis."""

from groq import Groq
from typing import Any, Dict
import time
import logging


class GroqClient:
    """Client for interacting with Groq API."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
        self._call_timestamps: list[float] = []

    def initialize(self):
        """Initialize the Groq client."""
        try:
            self.client = Groq(api_key=self.config['GROQ_API_KEY'])
            log = self.config.get('log', logging.getLogger(__name__))
            log.info("Groq client initialized.")
        except Exception as exc:
            log = self.config.get('log', logging.getLogger(__name__))
            log.error("Failed to initialize Groq client: %s", exc)

    def analyze(self, prompt: str) -> str:
        """Send prompt to Groq and return analysis."""
        if not self.client:
            return "Groq client not initialized."

        self._rate_limit()
        log = self.config.get('log', logging.getLogger(__name__))
        log.info("Sending prompt to Groq model '%s' …", self.config.get('GROQ_MODEL', 'llama3-8b-8192'))

        # Fix: Ensure prompt is never None or empty
        safe_prompt = str(prompt) if prompt else "No data available for analysis."

        try:
            response = self.client.chat.completions.create(
                model=self.config.get('GROQ_MODEL', 'llama3-8b-8192'),
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
            log.error("Groq API call failed: %s", exc)
            return f"Groq analysis failed: {exc}"

    def _rate_limit(self):
        """Enforce rate limiting."""
        now = time.monotonic()
        window = 60.0
        max_calls = self.config.get('GROQ_MAX_RPM', 30)

        self._call_timestamps = [t for t in self._call_timestamps if now - t < window]

        if len(self._call_timestamps) >= max_calls:
            sleep_for = window - (now - self._call_timestamps[0]) + 0.5
            log = self.config.get('log', logging.getLogger(__name__))
            log.info("Rate limit reached – sleeping %.1fs", sleep_for)
            time.sleep(sleep_for)

        self._call_timestamps.append(time.monotonic())
