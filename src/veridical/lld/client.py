"""A lightweight, asynchronous client for OpenAI-compatible LLM endpoints."""
import logging
from typing import cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from veridical.config.schema import LocalLLMConfig

logger = logging.getLogger(__name__)


class LLDClient:
    """A client for interacting with a local LLM endpoint."""

    def __init__(self, config: LocalLLMConfig) -> None:
        """Initialize the LLDClient.

        Args:
            config: Configuration for the local LLM.
        """
        self._config = config
        self._client = AsyncOpenAI(
            base_url=config.base_url,
            timeout=config.timeout,
            # The API key can be anything for local LLMs, but the client requires one.
            api_key="local-llm",
        )

    async def summarize_text(self, text: str, prompt: str) -> str:
        """Summarize a piece of text using the LLM.

        Args:
            text: The text to summarize.
            prompt: The system prompt to guide the summarization.

        Returns:
            The summarized text.
        """
        try:
            response = await self._client.chat.completions.create(
                model=self._config.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
                max_tokens=1024,
            )
            completion = cast(ChatCompletion, response)
            if completion.choices and completion.choices[0].message.content:
                return completion.choices[0].message.content.strip()
            return ""
        except Exception as e:
            logger.error(f"Error calling local LLM: {e}", exc_info=True)
            return ""
