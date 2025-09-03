from loguru import logger
import httpx
import openai
from openai import AsyncOpenAI
from starlette.datastructures import Secret


class Openai:
    """Async-compatible wrapper around the OpenAI Responses API."""

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
        self.client = AsyncOpenAI(api_key=key)

    async def send_prompt(self, prompt: str, model: str = "gpt-4o-mini") -> str:
        """Send a prompt asynchronously and return the text response."""
        logger.debug(
            "OpenAI client: dispatching prompt (len={}, model={})",
            len(prompt),
            model,
        )
        try:
            response = await self.client.responses.create(
                model=model,
                input=prompt,
                store=True,
                timeout=30,
            )
        except (openai.Timeout, httpx.TimeoutException) as exc:
            raise RuntimeError("OpenAI request timed out") from exc

        text = (response.output_text or "").strip()
        logger.debug(
            "OpenAI client: received response (len={})",
            len(text),
        )

        truncated = text[:200] + ("..." if len(text) > 200 else "")
        logger.debug("OpenAI client: response text: {}", truncated)

        return response.output_text

    async def __aenter__(self) -> "Openai":
        # No persistent connection to manage, but we keep the pattern
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        # No cleanup needed for the OpenAI SDK
        pass
