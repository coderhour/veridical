"""OpenAI-compatible API client."""

import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from veridical.config.schema import LocalLLMConfig

logger = logging.getLogger(__name__)


class LLDClient:
    """Client for interacting with a local LLM."""

    def __init__(self, config: LocalLLMConfig) -> None:
        """Initialize the LLDClient."""
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def get_completion(self, prompt: str) -> str:
        """Get a completion from the local LLM."""
        logger.info(f"Sending completion request to model {self.config.model}")
        try:
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": self.config.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise
        except Exception:
            logger.exception("An unexpected error occurred during completion request")
            raise
