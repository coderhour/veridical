"""Tests for the local LLM dispatcher."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from veridical.config.schema import LocalLLMConfig
from veridical.lld.client import LocalLLMClient, OpenAIImportError


@pytest.fixture
def mock_config() -> LocalLLMConfig:
    """Return a mock local LLM config."""
    return LocalLLMConfig(
        base_url="http://localhost:11434/v1",
        model="llama3",
        timeout=120,
    )


@patch("veridical.lld.client.AsyncOpenAI")
def test_client_initialization(
    mock_async_openai: MagicMock, mock_config: LocalLLMConfig
) -> None:
    """Test that the client is initialized correctly."""
    client = LocalLLMClient(config=mock_config)
    assert client.config == mock_config
    mock_async_openai.assert_called_once_with(
        base_url=mock_config.base_url,
        timeout=mock_config.timeout,
        api_key="local",
    )


def test_client_initialization_no_openai(mock_config: LocalLLMConfig) -> None:
    """Test that an error is raised if openai is not installed."""
    with patch("veridical.lld.client.AsyncOpenAI", None):
        with pytest.raises(OpenAIImportError):
            LocalLLMClient(config=mock_config)


@pytest.mark.asyncio
async def test_get_completion(mock_config: LocalLLMConfig) -> None:
    """Test getting a completion from the local LLM."""
    with patch("veridical.lld.client.AsyncOpenAI") as mock_async_openai:
        mock_client_instance = mock_async_openai.return_value
        mock_client_instance.chat.completions.create = AsyncMock()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test completion"
        mock_client_instance.chat.completions.create.return_value = mock_response

        client = LocalLLMClient(config=mock_config)
        completion = await client.get_completion("Test prompt")

        assert completion == "Test completion"
        mock_client_instance.chat.completions.create.assert_awaited_once_with(
            model="llama3",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Test prompt"},
            ],
        )
