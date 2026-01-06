import os

import pytest

from veridical.config.schema import LocalLLMConfig, VerifierConfig
from veridical.lld.client import LocalLLMClient
from veridical.models.result import GateResult, GateStatus, VerificationResult
from veridical.verifier.feedback import FeedbackGenerator

# Check for environment variables to enable the test
# This allows the test to be skipped if a local LLM is not available
# without failing the test suite.
_llm_base_url = os.getenv("VERIDICAL_TEST_LLM_BASE_URL")
_llm_model = os.getenv("VERIDICAL_TEST_LLM_MODEL")

# Create a skip condition
llm_not_configured = not (_llm_base_url and _llm_model)
llm_skip_reason = "VERIDICAL_TEST_LLM_BASE_URL and VERIDICAL_TEST_LLM_MODEL must be set"


@pytest.mark.slow
@pytest.mark.skipif(llm_not_configured, reason=llm_skip_reason)
class TestLLMFeedbackIntegration:
    """Integration tests for LLM feedback generation.

    These tests require a running OpenAI-compatible LLM endpoint.
    """

    @pytest.fixture
    def llm_config(self) -> LocalLLMConfig:
        """Provides LLM configuration from environment variables."""
        return LocalLLMConfig(
            base_url=_llm_base_url,
            model=_llm_model,
            api_key="ollama",  # Default for Ollama, can be overridden if needed
            timeout=60,
        )

    @pytest.fixture
    def verifier_config(self, llm_config: LocalLLMConfig) -> VerifierConfig:
        """Provides VerifierConfig with the LLM integration enabled."""
        return VerifierConfig(
            local_llm=llm_config,
            feedback_mode="rlm",  # Force RLM for testing
        )

    @pytest.mark.asyncio
    async def test_end_to_end_summarization(
        self, llm_config: LocalLLMConfig, verifier_config: VerifierConfig
    ):
        """Test end-to-end summarization of a realistic log file."""
        # A sample pytest failure log
        log_content = """
============================= test session starts ==============================
...
collected 1 item

test_example.py F                                                        [100%]

=================================== FAILURES ===================================
_________________________________ test_addition _________________________________

    def test_addition():
>       assert 1 + 1 == 3
E       assert (2 == 3)

test_example.py:5: AssertionError
=========================== short test summary info ============================
FAILED test_example.py::test_addition - assert (2 == 3)
============================== 1 failed in 0.03s ===============================
"""
        gate_result = GateResult(
            name="pytest",
            status=GateStatus.FAILED,
            output=log_content,
            duration_seconds=1.0,
        )
        verification_result = VerificationResult(
            passed=False, gates=[gate_result], duration_seconds=1.0
        )

        async with LocalLLMClient(llm_config) as llm_client:
            generator = FeedbackGenerator(config=verifier_config, llm_client=llm_client)
            feedback = await generator.generate_feedback(verification_result)

        # Assertions
        assert "pytest" in feedback
        # The key assertion: the LLM should extract the file, line, and message
        assert "test_example.py:5: AssertionError" in feedback
        # The LLM should not include the boilerplate
        assert "test session starts" not in feedback
        assert "short test summary info" not in feedback
