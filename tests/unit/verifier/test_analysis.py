"""Unit tests for the LogAnalyzer."""

import pytest
from unittest.mock import AsyncMock, patch

from veridical.lld.client import LLDClient
from veridical.verifier.analysis import (
    COMBINATION_PROMPT,
    MAX_CHUNK_TOKENS,
    SUMMARIZATION_PROMPT,
    LogAnalyzer,
)


@pytest.fixture
def mock_lld_client() -> AsyncMock:
    """Fixture for a mocked LLDClient."""
    client = AsyncMock(spec=LLDClient)
    client.summarize_text = AsyncMock(return_value="Mocked summary.")
    return client


@pytest.fixture
def log_analyzer(mock_lld_client: AsyncMock) -> LogAnalyzer:
    """Fixture for a LogAnalyzer instance with a mocked client."""
    return LogAnalyzer(client=mock_lld_client)


@pytest.mark.unit
class TestLogAnalyzer:
    """Tests for the LogAnalyzer class."""

    def test_initialization(self, mock_lld_client: AsyncMock) -> None:
        """Test that the LogAnalyzer initializes correctly."""
        analyzer = LogAnalyzer(client=mock_lld_client)
        assert analyzer._client is mock_lld_client
        assert analyzer._tokenizer is not None

    def test_count_tokens(self, log_analyzer: LogAnalyzer) -> None:
        """Test the token counting functionality."""
        text = "This is a simple test sentence."
        # Token count can vary slightly based on the tokenizer, so we use a range.
        assert 5 <= log_analyzer._count_tokens(text) <= 10

    def test_chunk_text(self, log_analyzer: LogAnalyzer) -> None:
        """Test the text chunking logic."""
        line = "This is a test line with some content.\n"
        # Create a multi-line string that is guaranteed to be chunked.
        long_text = line * (MAX_CHUNK_TOKENS // log_analyzer._count_tokens(line) + 100)
        chunks = log_analyzer._chunk_text(long_text)
        assert len(chunks) > 1
        for chunk in chunks:
            assert log_analyzer._count_tokens(chunk) <= MAX_CHUNK_TOKENS

    def test_chunk_text_single_long_line(self, log_analyzer: LogAnalyzer) -> None:
        """Test that a single long line is handled correctly."""
        long_line = "a" * (MAX_CHUNK_TOKENS * 2)
        chunks = log_analyzer._chunk_text(long_line)
        assert len(chunks) == 1
        assert chunks[0] == long_line

    @pytest.mark.asyncio
    async def test_analyze_log_short(
        self, log_analyzer: LogAnalyzer, mock_lld_client: AsyncMock
    ) -> None:
        """Test analyzing a log that is shorter than the context window."""
        short_log = "This is a short log with an error."
        await log_analyzer.analyze_log(short_log)
        mock_lld_client.summarize_text.assert_called_once_with(short_log, SUMMARIZATION_PROMPT)

    @pytest.mark.asyncio
    async def test_analyze_log_long(
        self, log_analyzer: LogAnalyzer, mock_lld_client: AsyncMock
    ) -> None:
        """Test analyzing a log that requires chunking and recursive summarization."""
        # Create a log that is guaranteed to be split into two chunks
        line = "This is a single line of log output that will be repeated.\n"
        line_tokens = log_analyzer._count_tokens(line)
        lines_for_one_chunk = MAX_CHUNK_TOKENS // line_tokens
        long_log = line * (lines_for_one_chunk + 50)  # Make it larger to be safe

        chunk_summaries = ["Summary of chunk 1.", "Summary of chunk 2."]
        final_summary = "Final combined summary."

        async def mock_summarize(text: str, prompt: str) -> str:
            if prompt == SUMMARIZATION_PROMPT:
                if chunk_summaries:
                    return chunk_summaries.pop(0)
                else:
                    pytest.fail("Summarization called too many times")
            elif prompt == COMBINATION_PROMPT:
                return final_summary
            else:
                pytest.fail(f"Unexpected prompt: {prompt}")
            return "fallback"  # Should be unreachable

        mock_lld_client.summarize_text.side_effect = mock_summarize

        result = await log_analyzer.analyze_log(long_log)

        assert result == final_summary
        assert mock_lld_client.summarize_text.call_count == 3
        assert not chunk_summaries
