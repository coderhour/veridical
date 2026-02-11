from pathlib import Path

import pytest

from veridical.config.schema import VerifierConfig
from veridical.diagnose import Localizer
from veridical.models.result import GateResult, GateSeverity, GateStatus, VerificationResult
from veridical.verifier.feedback import FeedbackGenerator


@pytest.mark.asyncio
async def test_feedback_enrichment():
    config = VerifierConfig(summary_max_length=1000, feedback_mode="heuristic", quality_gates=[])

    # Create a localizer and feedback generator
    localizer = Localizer(Path.cwd())
    generator = FeedbackGenerator(config=config, localizer=localizer)

    # Simulate a failed gate with a traceback
    gate_result = GateResult(
        name="pytest",
        status=GateStatus.FAILED,
        severity=GateSeverity.FAIL,
        output="""
Traceback (most recent call last):
  File "src/app.py", line 10, in main
    func()
ValueError: bug here
""",
        exit_code=1,
        duration_seconds=1.0,
    )

    verification_result = VerificationResult(
        passed=False, gates=[gate_result], duration_seconds=1.0
    )

    feedback = await generator.generate_feedback(verification_result)

    assert "Root cause likely in src/app.py:10" in feedback
    assert "## pytest (exit code 1)" in feedback
