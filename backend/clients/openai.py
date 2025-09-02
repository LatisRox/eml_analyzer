from loguru import logger
from openai import AsyncOpenAI
from starlette.datastructures import Secret

from backend import settings


class Openai:
    """Async client wrapper for the OpenAI Responses API."""

    def __init__(self, api_key: Secret, timeout: float | None = None):
        key = (
            api_key.get_secret_value()
            if hasattr(api_key, "get_secret_value")
            else str(api_key)
        )
        if not key:
            logger.debug("OpenAI API key is missing or empty.")
            raise ValueError("OpenAI API key is missing.")
        logger.debug("OpenAI API key loaded successfully.")
        timeout = timeout if timeout is not None else settings.OPENAI_TIMEOUT
        self.client = AsyncOpenAI(api_key=key, timeout=timeout)

    async def send_prompt(self, prompt: str, model: str = "gpt-5o") -> str:
        """Send a prompt to OpenAI asynchronously and return the reply."""
        logger.debug("Sending prompt to OpenAI with model `{}`", model)
        logger.debug("Prompt content: {}", prompt)
        completion = await self.client.responses.create(
            model=model,
            input=prompt,
        )
        response = completion.output_text.strip()
        logger.debug("Received response from OpenAI: {}", response)
        return response

    async def __aenter__(self) -> "Openai":
        # No persistent connection to manage, but we keep the pattern
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        # No cleanup needed for the OpenAI SDK
        pass
