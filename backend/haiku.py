from __future__ import annotations

import os
from loguru import logger
from openai import OpenAI


def generate_haiku() -> str:
    """Generate a haiku about AI using OpenAI's Responses API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.debug("OPENAI_API_KEY not set; skipping haiku generation")
        return ""

    logger.debug("Requesting haiku from OpenAI")
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model="gpt-4o-mini",
        input="write a haiku about ai",
        store=True,
    )
    text = response.output_text
    logger.debug("Received haiku: {}", text)
    print(text)
    return text
