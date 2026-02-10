from unittest.mock import AsyncMock, patch

import pytest

from veridical.config.schema import LocalLLMConfig
from veridical.verifier.analysis import LogAnalyzer


@pytest.mark.integration
@pytest.mark.filterwarnings("ignore::ResourceWarning")
@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
class TestRLMLargeLog:
    @pytest.fixture(autouse=True)
    def mock_logger(self):
        """Mock logger to prevent 'I/O operation on closed file' errors."""
        with patch("veridical.verifier.analysis.logger") as mock:
            yield mock

    @pytest.fixture
    def llm_config(self) -> LocalLLMConfig:
        """Create test LLM configuration."""
        return LocalLLMConfig(
            base_url="http://localhost:11434/v1",
            model="test-model",
            api_key="test-key",
            timeout=30,
            chunk_size=500,
        )

    @pytest.fixture
    def large_log_output(self) -> str:
        """Generate a large log file with multiple errors."""
        lines = []

        for i in range(1, 10001):
            if i % 1000 == 0:
                lines.append(f"ERROR: Critical failure at iteration {i}")
                lines.append("  Traceback (most recent call last):")
                lines.append(f"    File 'test.py', line {i}, in test_function")
                lines.append("      assert result == expected")
                lines.append(f"  AssertionError: {i} != {i + 1}")
            elif i % 500 == 0:
                lines.append(f"WARNING: Performance degradation at line {i}")
            else:
                lines.append(f"[{i:05d}] Processing item {i}: status=ok, duration=0.{i % 100}ms")

        return "\n".join(lines)

    @pytest.mark.asyncio
    async def test_large_log_chunking_behavior(
        self, llm_config: LocalLLMConfig, large_log_output: str
    ) -> None:
        """Test that large logs are properly chunked and analyzed."""
        analyzer = LogAnalyzer(llm_config)

        chunk_analyses = []

        def mock_complete_side_effect(prompt: str, **_kwargs):
            if "ERROR: Critical failure" in prompt:
                analysis = "Found critical error in chunk with assertion failure"
                chunk_analyses.append(analysis)
                return analysis
            elif "WARNING: Performance" in prompt:
                return "Found performance warning"
            else:
                return "NO ERRORS IN THIS CHUNK"

        with patch("veridical.verifier.analysis.LocalLLMClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.complete.side_effect = mock_complete_side_effect
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await analyzer.analyze_log(large_log_output, "large-test")

            total_lines = len(large_log_output.splitlines())
            expected_chunks = (total_lines + llm_config.chunk_size - 1) // llm_config.chunk_size

            assert mock_client.complete.call_count == expected_chunks
            assert "large-test" in result
            assert len(chunk_analyses) > 0

    @pytest.mark.asyncio
    async def test_recursive_summary_with_large_log(
        self, llm_config: LocalLLMConfig, large_log_output: str
    ) -> None:
        """Test that recursive summaries build up correctly."""
        analyzer = LogAnalyzer(llm_config)

        call_count = 0

        def mock_complete_with_summary_check(prompt: str, **_kwargs):
            nonlocal call_count
            call_count += 1

            if call_count > 1:
                assert "Previous summary" in prompt

            if "ERROR: Critical failure" in prompt:
                return f"Error found in chunk {call_count}"
            return "NO ERRORS IN THIS CHUNK"

        with patch("veridical.verifier.analysis.LocalLLMClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.complete.side_effect = mock_complete_with_summary_check
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await analyzer.analyze_log(large_log_output, "recursive-test")

            assert call_count > 1
            assert "recursive-test" in result

    @pytest.mark.asyncio
    async def test_performance_with_large_log(
        self, llm_config: LocalLLMConfig, large_log_output: str
    ) -> None:
        """Test that large log analysis completes in reasonable time."""
        import time

        analyzer = LogAnalyzer(llm_config)

        with patch("veridical.verifier.analysis.LocalLLMClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.complete.return_value = "NO ERRORS IN THIS CHUNK"
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            start_time = time.monotonic()
            result = await analyzer.analyze_log(large_log_output, "perf-test")
            duration = time.monotonic() - start_time

            assert duration < 5.0
            assert "perf-test" in result

    @pytest.mark.asyncio
    async def test_chunk_size_configuration(self, large_log_output: str) -> None:
        """Test that chunk_size configuration is respected."""
        custom_chunk_size = 100
        config = LocalLLMConfig(
            base_url="http://localhost:11434/v1",
            model="test-model",
            timeout=30,
            chunk_size=custom_chunk_size,
        )

        analyzer = LogAnalyzer(config)

        with patch("veridical.verifier.analysis.LocalLLMClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.complete.return_value = "NO ERRORS IN THIS CHUNK"
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await analyzer.analyze_log(large_log_output, "chunk-size-test")

            total_lines = len(large_log_output.splitlines())
            expected_chunks = (total_lines + custom_chunk_size - 1) // custom_chunk_size

            assert mock_client.complete.call_count == expected_chunks
