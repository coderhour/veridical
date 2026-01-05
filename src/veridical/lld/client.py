"""OpenAI-compatible client for local LLM endpoints."""

import logging
from typing import Any

import httpx

from veridical.config.schema import LocalLLMConfig
from veridical.exceptions import VerificationError

logger = logging.getLogger(__name__)


class LocalLLMClient:
    """Client for interacting with OpenAI-compatible local LLM endpoints."""

    def __init__(self, config: LocalLLMConfig) -> None:
        """Initialize the local LLM client.

        Args:
            config: Configuration for the local LLM endpoint.
        """
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.model = config.model
        self.timeout = config.timeout

        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=httpx.Timeout(self.timeout),
        )

    async def complete(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> str:
        """Send a completion request to the local LLM.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system prompt.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum tokens to generate.

        Returns:
            The generated completion text.

        Raises:
            VerificationError: If the request fails or times out.
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            if "choices" not in data or not data["choices"]:
                raise VerificationError(
                    "Invalid response from local LLM",
                    details="No choices in response",
                )

            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise VerificationError(
                    "Invalid response from local LLM",
                    details="Content is not a string",
                )
            return content.strip()

        except httpx.TimeoutException as e:
            logger.warning(f"Local LLM request timed out after {self.timeout}s")
            raise VerificationError(
                "Local LLM request timed out",
                details=f"Timeout after {self.timeout}s",
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Local LLM HTTP error: {e.response.status_code}")
            raise VerificationError(
                "Local LLM HTTP error",
                details=f"Status {e.response.status_code}: {e.response.text}",
            ) from e
        except Exception as e:
            logger.error(f"Local LLM request failed: {e}")
            raise VerificationError(
                "Local LLM request failed",
                details=str(e),
            ) from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self) -> "LocalLLMClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()
