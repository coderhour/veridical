"""Integration tests for the Verifier component."""

from pathlib import Path

import pytest

from veridical.config.schema import QualityGate, VeridicalConfig, VerifierConfig
from veridical.verifier.quality_gate import Verifier


@pytest.mark.integration
async def test_verifier_with_task_completion_gate_success(tmp_path: Path) -> None:
    """Test the Verifier with a successful task_completion gate."""
    # Create a mock tasks.md file
    tasks_md_path = "test_tasks.md"
    tasks_md = tmp_path / tasks_md_path
    tasks_md.write_text("- [x] Task 1\n- [x] Task 2\n")

    # Create a config with the task_completion gate
    config = VeridicalConfig(
        verifier=VerifierConfig(
            quality_gates=[
                QualityGate(
                    name="task_check",
                    type="task_completion",
                    path=tasks_md_path,
                )
            ]
        )
    )

    # Run the verifier
    verifier = Verifier(config, tmp_path)
    result = await verifier.run_all()

    # Assert the result
    assert result.passed is True
    assert len(result.gates) == 1
    assert result.gates[0].name == "task_check"
    assert result.gates[0].passed is True


@pytest.mark.integration
async def test_verifier_with_task_completion_gate_failure(tmp_path: Path) -> None:
    """Test the Verifier with a failing task_completion gate."""
    # Create a mock tasks.md file with an incomplete task
    tasks_md_path = "test_tasks.md"
    tasks_md = tmp_path / tasks_md_path
    tasks_md.write_text("- [x] Task 1\n- [ ] Task 2\n")

    # Create a config with the task_completion gate
    config = VeridicalConfig(
        verifier=VerifierConfig(
            quality_gates=[
                QualityGate(
                    name="task_check",
                    type="task_completion",
                    path=tasks_md_path,
                )
            ]
        )
    )

    # Run the verifier
    verifier = Verifier(config, tmp_path)
    result = await verifier.run_all()

    # Assert the result
    assert result.passed is False
    assert len(result.gates) == 1
    assert result.gates[0].name == "task_check"
    assert result.gates[0].passed is False
    assert "Task 2" in result.gates[0].error_output
