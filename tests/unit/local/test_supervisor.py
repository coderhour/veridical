import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from veridical.config.schema import (
    LocalConfig,
    SupervisorConfig,
    VeridicalConfig,
    VerifierConfig,
    WorkLogConfig,
)
from veridical.local.supervisor import LocalSupervisor
from veridical.models.result import VerificationResult


@pytest.fixture
def config():
    return VeridicalConfig(
        local=LocalConfig(
            worker_command="echo hello",
            worker_timeout=10,
            mode="subprocess",
        ),
        supervisor=SupervisorConfig(
            max_iterations=5,
            max_consecutive_failures=3,
        ),
        verifier=VerifierConfig(quality_gates=[]),
        worklog=WorkLogConfig(enabled=False),
    )


@pytest.fixture
def console():
    return MagicMock(spec=Console)


@pytest.fixture
def repo_path(tmp_path):
    return tmp_path


@pytest.mark.asyncio
async def test_supervisor_run_success(config, console, repo_path):
    supervisor = LocalSupervisor(config, repo_path, console=console)

    # Mock runner
    supervisor.runner.run = AsyncMock(return_value=0)

    # Mock verifier
    supervisor.verifier.run_all = AsyncMock(
        return_value=VerificationResult(
            passed=True, gates=[], duration_seconds=1.0, timestamp=datetime.now()
        )
    )

    result = await supervisor.run("Fix bug")

    assert result.success is True
    assert result.iterations == 1
    supervisor.runner.run.assert_called_once()
    supervisor.verifier.run_all.assert_called_once()


@pytest.mark.asyncio
async def test_supervisor_retry_loop(config, console, repo_path):
    supervisor = LocalSupervisor(config, repo_path, console=console)

    # Mock runner
    supervisor.runner.run = AsyncMock(return_value=0)

    # Mock verifier
    # First run fails, second run passes
    fail_result = VerificationResult(
        passed=False, gates=[], duration_seconds=1.0, timestamp=datetime.now()
    )
    pass_result = VerificationResult(
        passed=True, gates=[], duration_seconds=1.0, timestamp=datetime.now()
    )
    supervisor.verifier.run_all = AsyncMock(side_effect=[fail_result, pass_result])
    supervisor.verifier.generate_feedback = AsyncMock(return_value="Error context")

    result = await supervisor.run("Fix bug")

    assert result.success is True
    assert result.iterations == 2
    assert supervisor.runner.run.call_count == 2

    # Check that error context was passed to second run
    supervisor.runner.run.assert_called_with("Error context")


@pytest.mark.asyncio
async def test_supervisor_max_iterations(config, console, repo_path):
    config.supervisor.max_iterations = 2
    supervisor = LocalSupervisor(config, repo_path, console=console)

    supervisor.runner.run = AsyncMock(return_value=0)
    fail_result = VerificationResult(
        passed=False, gates=[], duration_seconds=1.0, timestamp=datetime.now()
    )
    supervisor.verifier.run_all = AsyncMock(return_value=fail_result)
    supervisor.verifier.generate_feedback = AsyncMock(return_value="Error context")

    result = await supervisor.run("Fix bug")

    assert result.success is False
    assert result.iterations == 2
    assert result.failure_reason == "Maximum iterations exceeded"
