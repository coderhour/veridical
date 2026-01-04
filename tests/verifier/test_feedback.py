import pytest
import respx
from httpx import Response

from veridical.config.schema import LocalLLMConfig
from veridical.models.result import GateResult, VerificationResult
from veridical.verifier.feedback import FeedbackGenerator

@pytest.fixture
def failed_verification_result():
    """Fixture for a failed verification result."""
    return VerificationResult(
        passed=False,
        gates=[
            GateResult(
                name="pytest",
                status="failed",
                output="Test failed.",
                error_output="An error occurred.",
                exit_code=1,
                duration_seconds=1.0,
            )
        ],
        duration_seconds=1.0,
    )

@pytest.mark.asyncio
async def test_feedback_generator_without_llm(failed_verification_result):
    """Test feedback generation without a local LLM configured."""
    # Arrange
    generator = FeedbackGenerator(max_length=100)

    # Act
    feedback = await generator.generate_feedback(failed_verification_result)

    # Assert
    assert "## pytest (exit code 1)" in feedback
    assert "An error occurred." in feedback

@pytest.mark.asyncio
@respx.mock
async def test_feedback_generator_with_llm(failed_verification_result):
    """Test feedback generation with a local LLM configured."""
    # Arrange
    llm_config = LocalLLMConfig(
        base_url="http://localhost:11434/v1",
        model="test-model",
        timeout=120,
    )

    # Mock the API response
    respx.post("http://localhost:11434/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "LLM-generated summary."}}
                ]
            },
        )
    )

    generator = FeedbackGenerator(max_length=100, local_llm_config=llm_config)

    # Act
    feedback = await generator.generate_feedback(failed_verification_result)

    # Assert
    assert "## pytest (exit code 1)" in feedback
    assert "LLM-generated summary." in feedback
