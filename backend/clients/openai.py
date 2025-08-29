import asyncio

from loguru import logger
from openai import OpenAI
from starlette.datastructures import Secret


class Openai:
    """Async-compatible client wrapper for the OpenAI ChatGPT API."""

    def __init__(self, api_key: Secret):
        key = (
            api_key.get_secret_value()
            if hasattr(api_key, "get_secret_value")
            else str(api_key)
        )
        if not key:
            logger.debug("OpenAI API key is missing or empty.")
            raise ValueError("OpenAI API key is missing.")
        logger.debug("OpenAI API key loaded successfully.")
        self.client = OpenAI(api_key=key)

    async def send_prompt(self, prompt: str, model: str = "gpt-3.5-turbo") -> str:
        """Send a prompt to ChatGPT asynchronously and return the reply."""
        completion = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content.strip()

    async def __aenter__(self) -> "Openai":
        # No persistent connection to manage, but we keep the pattern
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        # No cleanup needed for the OpenAI SDK
        pass
