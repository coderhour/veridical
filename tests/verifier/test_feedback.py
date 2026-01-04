"""Tests for the feedback generator."""

from unittest.mock import AsyncMock, patch

import pytest

from veridical.config.schema import LocalLLMConfig
from veridical.lld.client import LocalLLMClient
from veridical.models.result import GateResult, GateStatus, VerificationResult
from veridical.verifier.analysis import LogAnalyzer
from veridical.verifier.feedback import FeedbackGenerator


@pytest.fixture
def mock_llm_client() -> LocalLLMClient:
    """Return a mock local LLM client."""
    with patch("veridical.lld.client.AsyncOpenAI"):
        config = LocalLLMConfig()
        client = LocalLLMClient(config=config)
        client.get_completion = AsyncMock()
        return client


@pytest.fixture
def mock_log_analyzer(mock_llm_client: LocalLLMClient) -> LogAnalyzer:
    """Return a mock log analyzer."""
    analyzer = LogAnalyzer(client=mock_llm_client)
    analyzer.analyze_log = AsyncMock()
    return analyzer


@pytest.mark.asyncio
async def test_generate_feedback_passed() -> None:
    """Test feedback generation for a passed verification."""
    result = VerificationResult(
        passed=True,
        gates=[],
        duration_seconds=1.0,
    )
    generator = FeedbackGenerator()
    feedback = await generator.generate_feedback(result)
    assert feedback == ""


@pytest.mark.asyncio
async def test_generate_feedback_failed_no_analyzer() -> None:
    """Test feedback generation for a failed verification without a log analyzer."""
    gate_result = GateResult(
        name="test",
        status=GateStatus.FAILED,
        exit_code=1,
        output="a" * 1000,
        error_output="",
        duration_seconds=1.0,
    )
    result = VerificationResult(
        passed=False,
        gates=[gate_result],
        duration_seconds=1.0,
    )
    generator = FeedbackGenerator(max_length=500)
    feedback = await generator.generate_feedback(result)
    assert len(feedback) < 1000
    assert "..." in feedback


@pytest.mark.asyncio
async def test_generate_feedback_failed_with_analyzer(
    mock_log_analyzer: LogAnalyzer,
) -> None:
    """Test feedback generation for a failed verification with a log analyzer."""
    gate_result = GateResult(
        name="test",
        status=GateStatus.FAILED,
        exit_code=1,
        output="This is an error message.",
        error_output="",
        duration_seconds=1.0,
    )
    result = VerificationResult(
        passed=False,
        gates=[gate_result],
        duration_seconds=1.0,
    )
    mock_log_analyzer.analyze_log.return_value = "Analyzed summary"

    generator = FeedbackGenerator(analyzer=mock_log_analyzer)
    feedback = await generator.generate_feedback(result)

    assert "Analyzed summary" in feedback
    mock_log_analyzer.analyze_log.assert_awaited_once_with(
        "This is an error message."
    )
