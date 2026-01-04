"""Tests for the log analyzer."""

from unittest.mock import AsyncMock, patch

import pytest

from veridical.config.schema import LocalLLMConfig
from veridical.lld.client import LocalLLMClient
from veridical.verifier.analysis import LogAnalyzer, DEFAULT_CONTEXT_WINDOW


@pytest.fixture
def mock_llm_client() -> LocalLLMClient:
    """Return a mock local LLM client."""
    with patch("veridical.lld.client.AsyncOpenAI"):
        config = LocalLLMConfig()
        client = LocalLLMClient(config=config)
        client.get_completion = AsyncMock()
        return client


@pytest.mark.asyncio
async def test_analyze_log_small(mock_llm_client: LocalLLMClient) -> None:
    """Test analyzing a small log file."""
    log = "This is a small log file."
    mock_llm_client.get_completion.return_value = "Summary of small log"

    analyzer = LogAnalyzer(client=mock_llm_client)
    summary = await analyzer.analyze_log(log)

    assert summary == "Summary of small log"
    mock_llm_client.get_completion.assert_awaited_once()


@pytest.mark.asyncio
async def test_analyze_log_large(mock_llm_client: LocalLLMClient) -> None:
    """Test analyzing a large log file that requires chunking."""
    # This log will be split into two chunks
    log = "a" * (DEFAULT_CONTEXT_WINDOW + 2000)

    # Mock the LLM client to return summaries for each chunk, and a final summary
    summaries = [
        "Summary of chunk 1.",
        "Summary of chunk 2.",
        "Final summary of the two chunks.",
    ]
    mock_llm_client.get_completion.side_effect = lambda *args, **kwargs: summaries.pop(0)

    analyzer = LogAnalyzer(client=mock_llm_client)
    summary = await analyzer.analyze_log(log)

    assert summary == "Final summary of the two chunks."
    assert mock_llm_client.get_completion.call_count == 3


def test_get_token_count_no_tiktoken(mock_llm_client: LocalLLMClient) -> None:
    """Test token count when tiktoken is not available."""
    with patch("veridical.verifier.analysis.tiktoken", None):
        analyzer = LogAnalyzer(client=mock_llm_client)
        count = analyzer._get_token_count("some text")
        assert count == len("some text")
