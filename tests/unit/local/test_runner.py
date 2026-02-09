"""Tests for LocalRunner."""

from unittest.mock import MagicMock, patch

import pytest

from veridical.config.schema import LocalConfig
from veridical.local.runner import LocalRunner


@pytest.fixture
def local_config():
    """Create a local config for testing."""
    return LocalConfig(
        worker_command="echo",
        worker_timeout=10,
        mode="subprocess",
        error_env_var="TEST_ERROR",
    )


@pytest.fixture
def runner(local_config):
    """Create a LocalRunner instance."""
    return LocalRunner(local_config)


@pytest.mark.asyncio
async def test_run_subprocess_success(runner):
    """Test running a successful subprocess command."""
    runner.config.worker_command = "echo"
    runner.config.mode = "subprocess"

    # We can actually run "echo" since it's safe
    exit_code = await runner.run("hello")
    assert exit_code == 0


@pytest.mark.asyncio
async def test_run_subprocess_with_error_context(runner):
    """Test running a subprocess with error context."""
    # The command will be: sh -c '...' 'task'
    # 'task' becomes $0 inside the script, but we don't use it.
    runner.config.worker_command = 'sh -c \'if [ "$TEST_ERROR" = "fail" ]; then exit 1; fi\''
    runner.config.mode = "subprocess"

    exit_code = await runner.run("task", error_context="fail")
    assert exit_code == 1

    exit_code = await runner.run("task", error_context="pass")
    assert exit_code == 0


@pytest.mark.asyncio
async def test_run_interactive(runner):
    """Test running an interactive command."""
    runner.config.worker_command = "echo"
    runner.config.mode = "interactive"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        exit_code = await runner.run("hello")

        assert exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        # command string should contain echo hello (no quotes for safe string)
        assert "echo hello" in args[0]
        assert kwargs["shell"] is True


@pytest.mark.asyncio
async def test_run_subprocess_timeout(runner):
    """Test subprocess timeout."""
    # Use 'sh -c' to ensure 'task' arg is ignored by sleep
    runner.config.worker_command = "sh -c 'sleep 2'"
    runner.config.worker_timeout = 0.1
    runner.config.mode = "subprocess"

    # This might fail on some slow CI, but 0.1s for sleep 2 should be enough
    exit_code = await runner.run("task")
    assert exit_code == -1
