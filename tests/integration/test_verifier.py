"""Integration tests for the Verifier component."""

from pathlib import Path

import asyncio

import pytest
from unittest.mock import AsyncMock, patch

from veridical.config.schema import (
    LocalLLMConfig,
    QualityGate,
    VeridicalConfig,
    VerifierConfig,
)
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


@pytest.mark.integration
@patch("veridical.verifier.quality_gate.logger")
@patch("veridical.verifier.quality_gate.LLDClient")
async def test_verifier_with_llm_analyzer(
    mock_lld_client, mock_logger, tmp_path: Path
) -> None:
    """Test that Verifier initializes and uses LogAnalyzer when configured."""
    mock_client_instance = mock_lld_client.return_value
    mock_client_instance.summarize_text = AsyncMock(return_value="LLM summary")

    llm_config = LocalLLMConfig(base_url="http://mock", model="mock-model")
    config = VeridicalConfig(
        verifier=VerifierConfig(
            quality_gates=[
                QualityGate(name="failing_command", type="command", command="exit 1")
            ],
            local_llm=llm_config,
        )
    )

    verifier = Verifier(config, tmp_path)
    result = await verifier.run_all()
    feedback = await verifier.generate_feedback(result)

    assert "LLM summary" in feedback
    mock_client_instance.summarize_text.assert_called_once()


@pytest.mark.integration
@patch("veridical.verifier.quality_gate.LLDClient", None)
async def test_verifier_without_llm_packages(tmp_path: Path) -> None:
    """Test that Verifier falls back gracefully when LLM packages are not installed."""
    llm_config = LocalLLMConfig(base_url="http://mock", model="mock-model")
    config = VeridicalConfig(
        verifier=VerifierConfig(
            quality_gates=[
                QualityGate(name="failing_command", type="command", command="exit 1")
            ],
            local_llm=llm_config,
        )
    )

    verifier = Verifier(config, tmp_path)
    assert verifier.feedback_generator._analyzer is None

    result = await verifier.run_all()
    feedback = await verifier.generate_feedback(result)

    assert "LLM summary" not in feedback
    assert "..." in feedback or "(no output)" in feedback
