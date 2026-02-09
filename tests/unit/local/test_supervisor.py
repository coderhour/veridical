import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from veridical.config.schema import VeridicalConfig
from veridical.local.supervisor import LocalSupervisor, LoopResult
from veridical.models.result import LoopResult as ApiLoopResult


@pytest.fixture
def mock_console():
    console = MagicMock(spec=Console)
    console.is_jupyter = False
    return console


@pytest.fixture
def veridical_config():
    config = VeridicalConfig()
    config.local.worker_command = "echo test"
    return config


@pytest.fixture
def mock_progress_reporter():
    with patch("veridical.local.supervisor.ProgressReporter") as mock:
        yield mock


@pytest.mark.asyncio
async def test_supervisor_run_success(
    veridical_config, mock_console, tmp_path, mock_progress_reporter
):
    supervisor = LocalSupervisor(veridical_config, tmp_path, console=mock_console)
    supervisor.progress = mock_progress_reporter.return_value

    # Mock runner
    supervisor.runner.run = AsyncMock(return_value=0)

    # Mock verifier
    mock_verification_result = MagicMock()
    mock_verification_result.passed = True
    supervisor.verifier.run_all = AsyncMock(return_value=mock_verification_result)

    result = await supervisor.run("Test Task")

    assert result.success
    supervisor.runner.run.assert_called_once()
    supervisor.verifier.run_all.assert_called_once()


@pytest.mark.asyncio
async def test_supervisor_run_failure_loop(
    veridical_config, mock_console, tmp_path, mock_progress_reporter
):
    veridical_config.supervisor.max_iterations = 2
    supervisor = LocalSupervisor(veridical_config, tmp_path, console=mock_console)
    supervisor.progress = mock_progress_reporter.return_value

    # Mock runner
    supervisor.runner.run = AsyncMock(return_value=0)

    # Mock verifier to fail
    mock_fail_result = MagicMock()
    mock_fail_result.passed = False
    supervisor.verifier.run_all = AsyncMock(return_value=mock_fail_result)
    supervisor.verifier.generate_feedback = AsyncMock(return_value="Error context")

    result = await supervisor.run("Test Task")

    assert not result.success
    # Circuit breaker sets this message when max iterations is exceeded
    assert "Maximum iterations exceeded" in result.failure_reason
    assert supervisor.runner.run.call_count == 2
    assert supervisor.verifier.run_all.call_count == 2


@pytest.mark.asyncio
async def test_supervisor_run_success_after_failure(
    veridical_config, mock_console, tmp_path, mock_progress_reporter
):
    veridical_config.supervisor.max_iterations = 3
    supervisor = LocalSupervisor(veridical_config, tmp_path, console=mock_console)
    supervisor.progress = mock_progress_reporter.return_value

    # Mock runner
    supervisor.runner.run = AsyncMock(return_value=0)

    # Mock verifier sequence: Fail, Pass
    mock_fail_result = MagicMock()
    mock_fail_result.passed = False

    mock_pass_result = MagicMock()
    mock_pass_result.passed = True

    supervisor.verifier.run_all = AsyncMock(
        side_effect=[mock_fail_result, mock_pass_result]
    )
    supervisor.verifier.generate_feedback = AsyncMock(return_value="Error context")

    result = await supervisor.run("Test Task")

    assert result.success
    assert supervisor.runner.run.call_count == 2
    assert supervisor.verifier.run_all.call_count == 2

    # Check that error context was passed to second run
    supervisor.runner.run.assert_called_with("Error context")


@pytest.mark.asyncio
async def test_supervisor_logging(
    veridical_config, mock_console, tmp_path, mock_progress_reporter
):
    veridical_config.worklog.enabled = True
    supervisor = LocalSupervisor(veridical_config, tmp_path, console=mock_console)
    supervisor.progress = mock_progress_reporter.return_value

    # Mock writer
    supervisor.worklog_writer = MagicMock()
    supervisor.runner.run = AsyncMock(return_value=0)

    mock_verification_result = MagicMock()
    mock_verification_result.passed = True
    supervisor.verifier.run_all = AsyncMock(return_value=mock_verification_result)

    await supervisor.run("Test Task")

    supervisor.worklog_writer.write.assert_called()
    call_args = supervisor.worklog_writer.write.call_args[0][0]
    assert call_args.task_description == "Test Task"
    assert call_args.verification_passed is True
