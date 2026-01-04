"""Client for interacting with a local OpenAI-compatible LLM endpoint."""

import logging
from typing import cast

from veridical.config.schema import LocalLLMConfig
from veridical.exceptions import VeridicalError

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI
    from openai.types.chat import ChatCompletion
except ImportError:
    AsyncOpenAI = None  # type: ignore
    ChatCompletion = None  # type: ignore


class OpenAIImportError(VeridicalError):
    """Raised when openai is not installed for llm feature."""

    def __init__(self) -> None:
        """Initialize the exception."""
        super().__init__(
            "The 'openai' package is not installed. "
            "Please install it with `uv pip install veridical[llm]` to use this feature."
        )


class LocalLLMClient:
    """Client for local LLM interaction."""

    def __init__(self, config: LocalLLMConfig) -> None:
        """Initialize the client.

        Args:
            config: Configuration for the local LLM.

        Raises:
            OpenAIImportError: if openai is not installed.
        """
        if AsyncOpenAI is None:
            raise OpenAIImportError()

        self.config = config
        self._client = AsyncOpenAI(
            base_url=config.base_url,
            timeout=config.timeout,
            api_key="local",  # Required by the client, but not used for local servers
        )

    async def get_completion(self, prompt: str) -> str:
        """Get a completion from the local LLM.

        Args:
            prompt: The prompt to send to the LLM.

        Returns:
            The completion text.
        """
        logger.debug("Sending prompt to local LLM: %s", prompt)
        try:
            response = await self._client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
            )
            response = cast(ChatCompletion, response)
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Error getting completion from local LLM: %s", e)
            return ""

        return ""
