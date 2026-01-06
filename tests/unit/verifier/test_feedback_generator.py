import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from veridical.config.schema import VerifierConfig, LocalLLMConfig
from veridical.exceptions import VerificationError
from veridical.lld.client import LocalLLMClient
from veridical.models.result import GateResult, GateStatus, VerificationResult
from veridical.verifier.feedback import FeedbackGenerator


# Mocks
@pytest.fixture
def mock_gate_result_factory():
    def _factory(output: str, error_output: str = "", name: str = "test_gate"):
        return GateResult(
            name=name,
            status=GateStatus.FAILED,
            exit_code=1,
            output=output,
            error_output=error_output,
            duration_seconds=1.0,
        )

    return _factory


@pytest.fixture
def mock_llm_client():
    client = AsyncMock(spec=LocalLLMClient)
    client.complete = AsyncMock()
    # Mock the config attribute needed by the generator
    client.config = LocalLLMConfig(base_url="http://mock", model="mock-model", chunk_size=100)
    return client


@pytest.fixture
def base_verifier_config():
    return VerifierConfig()


# Tests
@pytest.mark.asyncio
async def test_generate_feedback_no_failed_gates():
    config = VerifierConfig()
    generator = FeedbackGenerator(config=config)
    result = VerificationResult(passed=True, gates=[], duration_seconds=1.0)
    feedback = await generator.generate_feedback(result)
    assert feedback == ""


@pytest.mark.asyncio
async def test_heuristic_mode(mock_gate_result_factory, base_verifier_config):
    config = base_verifier_config
    config.feedback_mode = "heuristic"

    gate_result = mock_gate_result_factory("Some output\n" * 20)
    verification_result = VerificationResult(
        passed=False, gates=[gate_result], duration_seconds=1.0
    )

    generator = FeedbackGenerator(config=config)

    with patch.object(generator, "compress_log_output", return_value="compressed") as mock_compress:
        feedback = await generator.generate_feedback(verification_result)
        mock_compress.assert_called_once()
        assert "compressed" in feedback


@pytest.mark.asyncio
async def test_rlm_mode_short_log(mock_gate_result_factory, base_verifier_config, mock_llm_client):
    config = base_verifier_config
    config.feedback_mode = "rlm"

    gate_result = mock_gate_result_factory("short log error")
    verification_result = VerificationResult(
        passed=False, gates=[gate_result], duration_seconds=1.0
    )

    mock_llm_client.complete.return_value = "llm summary"
    generator = FeedbackGenerator(config=config, llm_client=mock_llm_client)

    feedback = await generator.generate_feedback(verification_result)

    mock_llm_client.complete.assert_called_once()
    assert "llm summary" in feedback


@pytest.mark.asyncio
async def test_rlm_mode_long_log_recursive(
    mock_gate_result_factory, base_verifier_config, mock_llm_client
):
    config = base_verifier_config
    config.feedback_mode = "rlm"

    # Create a log longer than the mock chunk_size (100)
    long_log = "line\n" * 150
    gate_result = mock_gate_result_factory(long_log)
    verification_result = VerificationResult(
        passed=False, gates=[gate_result], duration_seconds=1.0
    )

    # Mock responses for chunk summarization and final summarization
    mock_llm_client.complete.side_effect = ["summary chunk 1", "summary chunk 2", "final summary"]
    generator = FeedbackGenerator(config=config, llm_client=mock_llm_client)

    feedback = await generator.generate_feedback(verification_result)

    assert mock_llm_client.complete.call_count == 3
    assert "final summary" in feedback


@pytest.mark.asyncio
async def test_auto_mode_below_threshold(mock_gate_result_factory, base_verifier_config):
    config = base_verifier_config
    config.feedback_mode = "auto"
    config.rlm_threshold = 50

    gate_result = mock_gate_result_factory("short log\n" * 10)
    verification_result = VerificationResult(
        passed=False, gates=[gate_result], duration_seconds=1.0
    )

    generator = FeedbackGenerator(config=config, llm_client=None)  # No LLM client needed

    with patch.object(generator, "compress_log_output", return_value="compressed") as mock_compress:
        feedback = await generator.generate_feedback(verification_result)
        mock_compress.assert_called_once()
        assert "compressed" in feedback


@pytest.mark.asyncio
async def test_auto_mode_above_threshold(
    mock_gate_result_factory, base_verifier_config, mock_llm_client
):
    config = base_verifier_config
    config.feedback_mode = "auto"
    config.rlm_threshold = 5

    gate_result = mock_gate_result_factory("long log\n" * 10)
    verification_result = VerificationResult(
        passed=False, gates=[gate_result], duration_seconds=1.0
    )

    mock_llm_client.complete.return_value = "llm summary"
    generator = FeedbackGenerator(config=config, llm_client=mock_llm_client)

    feedback = await generator.generate_feedback(verification_result)

    mock_llm_client.complete.assert_called_once()
    assert "llm summary" in feedback


@pytest.mark.asyncio
async def test_rlm_fallback_on_llm_failure(
    mock_gate_result_factory, base_verifier_config, mock_llm_client
):
    config = base_verifier_config
    config.feedback_mode = "rlm"

    gate_result = mock_gate_result_factory("some output")
    verification_result = VerificationResult(
        passed=False, gates=[gate_result], duration_seconds=1.0
    )

    mock_llm_client.complete.side_effect = VerificationError("LLM is down")
    generator = FeedbackGenerator(config=config, llm_client=mock_llm_client)

    with patch.object(
        generator, "compress_log_output", return_value="fallback compressed"
    ) as mock_compress:
        feedback = await generator.generate_feedback(verification_result)
        mock_compress.assert_called_once()
        assert "fallback compressed" in feedback
