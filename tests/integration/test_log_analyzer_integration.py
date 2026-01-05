import pytest
import respx
from httpx import Response

from veridical.config.schema import LocalLLMConfig
from veridical.exceptions import VerificationError
from veridical.verifier.analysis import LogAnalyzer


@pytest.mark.integration
class TestLogAnalyzerIntegration:
    @pytest.mark.asyncio
    @respx.mock
    async def test_end_to_end_log_analysis(self) -> None:
        """Test end-to-end log analysis with mocked HTTP server."""
        base_url = "http://test-server:8000"

        def mock_chat_response(request):
            """Mock chat completions endpoint."""
            content = request.content.decode()

            if "ERROR" in content or "error" in content.lower():
                response_text = "Analysis: Found error in the log output at the specified lines."
            else:
                response_text = "NO ERRORS IN THIS CHUNK"

            return Response(
                200,
                json={
                    "id": "test-completion-id",
                    "object": "chat.completion",
                    "created": 1234567890,
                    "model": "test-model",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": response_text},
                            "finish_reason": "stop",
                        }
                    ],
                },
            )

        respx.post(f"{base_url}/chat/completions").mock(side_effect=mock_chat_response)

        config = LocalLLMConfig(
            base_url=base_url,
            model="test-model",
            api_key="test-key",
            timeout=10,
            chunk_size=100,
        )

        analyzer = LogAnalyzer(config)

        log_output = """
Line 1
Line 2
Line 3
ERROR: Test failed at line 4
Line 5
Line 6
"""

        result = await analyzer.analyze_log(log_output.strip(), "pytest")

        assert "pytest" in result
        assert "error" in result.lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_large_log_with_server(self) -> None:
        """Test analysis of large log with chunking."""
        base_url = "http://test-server:8000"

        respx.post(f"{base_url}/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "id": "test-completion-id",
                    "object": "chat.completion",
                    "created": 1234567890,
                    "model": "test-model",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "Analysis: Found error in the log",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                },
            )
        )

        config = LocalLLMConfig(
            base_url=base_url,
            model="test-model",
            api_key="test-key",
            timeout=10,
            chunk_size=100,
        )

        analyzer = LogAnalyzer(config)

        lines = [f"Line {i}" for i in range(30)]
        lines[15] = "ERROR: Critical failure"
        log_output = "\n".join(lines)

        result = await analyzer.analyze_log(log_output, "integration-test")

        assert "integration-test" in result

    @pytest.mark.asyncio
    async def test_timeout_handling(self) -> None:
        """Test that timeout is properly handled."""
        config = LocalLLMConfig(
            base_url="http://localhost:99999",
            model="test-model",
            timeout=1,
            chunk_size=100,
        )

        analyzer = LogAnalyzer(config)
        log_output = "ERROR: Test error"

        with pytest.raises((VerificationError, Exception)):
            await analyzer.analyze_log(log_output, "pytest")
