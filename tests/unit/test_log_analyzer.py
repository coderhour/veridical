from unittest.mock import AsyncMock, patch

import pytest

from veridical.config.schema import LocalLLMConfig
from veridical.exceptions import VerificationError
from veridical.verifier.analysis import LogAnalyzer


@pytest.mark.unit
class TestLogAnalyzer:
    @pytest.fixture
    def llm_config(self) -> LocalLLMConfig:
        """Create a test LLM configuration."""
        return LocalLLMConfig(
            base_url="http://localhost:11434/v1",
            model="test-model",
            api_key="test-key",
            timeout=30,
            chunk_size=100,
        )

    @pytest.fixture
    def analyzer(self, llm_config: LocalLLMConfig) -> LogAnalyzer:
        """Create a LogAnalyzer instance."""
        return LogAnalyzer(llm_config)

    @pytest.mark.asyncio
    async def test_analyze_small_log(self, analyzer: LogAnalyzer) -> None:
        """Test analysis of a small log that fits in one chunk."""
        log_output = "\n".join([f"Line {i}" for i in range(5)])
        log_output += "\nERROR: Test failed at line 42"

        mock_response = "Found error: Test failed at line 42"

        with patch("veridical.verifier.analysis.LocalLLMClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.complete.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await analyzer.analyze_log(log_output, "pytest")

            assert "Found error: Test failed at line 42" in result
            assert "pytest" in result
            mock_client.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_large_log_chunking(self, analyzer: LogAnalyzer) -> None:
        """Test analysis of a large log that requires chunking."""
        lines = [f"Line {i}" for i in range(250)]
        lines[50] = "ERROR: First error"
        lines[150] = "ERROR: Second error"
        log_output = "\n".join(lines)

        mock_responses = [
            "Found error at line 11: First error",
            "Found error at line 21: Second error",
            "NO ERRORS IN THIS CHUNK",
        ]

        with patch("veridical.verifier.analysis.LocalLLMClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.complete.side_effect = mock_responses
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await analyzer.analyze_log(log_output, "pytest")

            assert "First error" in result
            assert "Second error" in result
            assert mock_client.complete.call_count == 3

    @pytest.mark.asyncio
    async def test_analyze_empty_log(self, analyzer: LogAnalyzer) -> None:
        """Test analysis of empty log output."""
        result = await analyzer.analyze_log("", "pytest")
        assert result == "(no output)"

    @pytest.mark.asyncio
    async def test_analyze_with_timeout(self, analyzer: LogAnalyzer) -> None:
        """Test handling of LLM timeout."""
        log_output = "ERROR: Something failed"

        with patch("veridical.verifier.analysis.LocalLLMClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.complete.side_effect = VerificationError(
                "Local LLM request timed out", details="Timeout after 30s"
            )
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(VerificationError) as exc_info:
                await analyzer.analyze_log(log_output, "pytest")

            assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_analyze_with_partial_failure(self, analyzer: LogAnalyzer) -> None:
        """Test that analysis continues when one chunk fails."""
        lines = [f"Line {i}" for i in range(250)]
        lines[50] = "ERROR: First error"
        lines[150] = "ERROR: Second error"
        log_output = "\n".join(lines)

        mock_responses = [
            "Found error at line 11: First error",
            VerificationError("Chunk analysis failed"),
            "Found error at line 21: Second error",
        ]

        with patch("veridical.verifier.analysis.LocalLLMClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.complete.side_effect = mock_responses
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await analyzer.analyze_log(log_output, "pytest")

            assert "First error" in result
            assert "Second error" in result

    @pytest.mark.asyncio
    async def test_analyze_no_errors_in_chunks(self, analyzer: LogAnalyzer) -> None:
        """Test that chunks with no errors don't pollute the summary."""
        lines = [f"Line {i}" for i in range(250)]
        log_output = "\n".join(lines)

        mock_responses = [
            "NO ERRORS IN THIS CHUNK",
            "NO ERRORS IN THIS CHUNK",
            "NO ERRORS IN THIS CHUNK",
        ]

        with patch("veridical.verifier.analysis.LocalLLMClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.complete.side_effect = mock_responses
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await analyzer.analyze_log(log_output, "pytest")

            assert "pytest" in result
            assert result.count("NO ERRORS IN THIS CHUNK") == 0

    @pytest.mark.asyncio
    async def test_recursive_summary_building(self, analyzer: LogAnalyzer) -> None:
        """Test that previous summaries are passed to subsequent chunks."""
        lines = [f"Line {i}" for i in range(250)]
        lines[50] = "ERROR: First error"
        lines[150] = "ERROR: Second error"
        log_output = "\n".join(lines)

        mock_responses = [
            "Found error at line 11: First error",
            "Found error at line 21: Second error (related to first)",
            "NO ERRORS IN THIS CHUNK",
        ]

        with patch("veridical.verifier.analysis.LocalLLMClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.complete.side_effect = mock_responses
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await analyzer.analyze_log(log_output, "pytest")

            assert "First error" in result
            assert "Second error" in result

            calls = mock_client.complete.call_args_list
            assert len(calls) == 3

            first_call_prompt = calls[0][1]["prompt"]
            assert "Previous summary" not in first_call_prompt

            second_call_prompt = calls[1][1]["prompt"]
            assert "Previous summary" in second_call_prompt
            assert "First error" in second_call_prompt
