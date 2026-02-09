"""Tests for LocalSupervisor."""

from unittest.mock import AsyncMock

import pytest

from veridical.config.schema import VeridicalConfig
from veridical.local.supervisor import LocalSupervisor
from veridical.models.result import VerificationResult


@pytest.fixture
def config():
    """Create a veridical config for testing."""
    config = VeridicalConfig()
    config.supervisor.max_iterations = 5
    config.local.worker_command = "echo"
    config.worklog.enabled = False
    return config


@pytest.fixture
def supervisor(config, tmp_path):
    """Create a LocalSupervisor instance."""
    return LocalSupervisor(config, tmp_path)


@pytest.mark.asyncio
async def test_run_success(supervisor):
    """Test a successful run."""
    supervisor.runner.run = AsyncMock(return_value=0)
    supervisor.verifier.run_all = AsyncMock(
        return_value=VerificationResult(
            passed=True,
            gates=[],
            duration_seconds=1.0,
        )
    )

    result = await supervisor.run("task")

    assert result.success
    assert result.iterations == 1
    supervisor.runner.run.assert_called_once()
    supervisor.verifier.run_all.assert_called_once()


@pytest.mark.asyncio
async def test_run_failure_loop(supervisor):
    """Test a run that fails and loops."""
    supervisor.runner.run = AsyncMock(return_value=0)

    # Fail first, pass second
    fail_result = VerificationResult(
        passed=False,
        gates=[],
        duration_seconds=1.0,
    )
    pass_result = VerificationResult(
        passed=True,
        gates=[],
        duration_seconds=1.0,
    )

    supervisor.verifier.run_all = AsyncMock(side_effect=[fail_result, pass_result])
    supervisor.verifier.generate_feedback = AsyncMock(return_value="error")

    result = await supervisor.run("task")

    assert result.success
    assert result.iterations == 2
    assert supervisor.runner.run.call_count == 2
    # First call with None context, second with "error"
    supervisor.runner.run.assert_any_call("task", None)
    supervisor.runner.run.assert_any_call("task", "error")


@pytest.mark.asyncio
async def test_max_iterations(supervisor):
    """Test reaching max iterations."""
    # Update circuit breaker directly as it's already initialized
    supervisor._circuit_breaker.max_iterations = 2
    supervisor.runner.run = AsyncMock(return_value=0)

    fail_result = VerificationResult(
        passed=False,
        gates=[],
        duration_seconds=1.0,
    )

    supervisor.verifier.run_all = AsyncMock(return_value=fail_result)
    supervisor.verifier.generate_feedback = AsyncMock(return_value="error")

    result = await supervisor.run("task")

    assert not result.success
    # Circuit breaker checks > max_iterations (2).
    # It runs 1, 2, then records 3 which trips it.
    assert result.iterations == 3
    assert result.failure_reason == "Maximum iterations exceeded"
