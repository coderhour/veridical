import asyncio
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from veridical.config.schema import LocalConfig
from veridical.local.runner import LocalRunner


@pytest.fixture
def mock_console():
    return MagicMock(spec=Console)


@pytest.fixture
def local_config():
    return LocalConfig(
        worker_command="echo test",
        worker_timeout=10,
        mode="subprocess",
        error_env_var="TEST_ERROR_CTX",
    )


@pytest.mark.asyncio
async def test_run_subprocess_success(local_config, mock_console):
    runner = LocalRunner(local_config, mock_console)

    # Mock asyncio.create_subprocess_shell
    process_mock = AsyncMock()
    process_mock.communicate.return_value = (b"output\n", b"")
    process_mock.returncode = 0

    with patch(
        "asyncio.create_subprocess_shell", return_value=process_mock
    ) as mock_shell:
        exit_code = await runner.run()

        assert exit_code == 0
        mock_shell.assert_called_once()
        args, kwargs = mock_shell.call_args
        assert args[0] == "echo test"
        assert kwargs["stdout"] == asyncio.subprocess.PIPE
        assert kwargs["stderr"] == asyncio.subprocess.PIPE


@pytest.mark.asyncio
async def test_run_subprocess_failure(local_config, mock_console):
    local_config.worker_command = "false"
    runner = LocalRunner(local_config, mock_console)

    process_mock = AsyncMock()
    process_mock.communicate.return_value = (b"", b"error\n")
    process_mock.returncode = 1

    with patch(
        "asyncio.create_subprocess_shell", return_value=process_mock
    ) as mock_shell:
        exit_code = await runner.run()

        assert exit_code == 1


@pytest.mark.asyncio
async def test_run_subprocess_timeout(local_config, mock_console):
    local_config.worker_timeout = 0.1
    runner = LocalRunner(local_config, mock_console)

    process_mock = AsyncMock()
    # Simulate timeout by sleeping longer than timeout
    async def delayed_communicate():
        await asyncio.sleep(0.2)
        return (b"", b"")

    process_mock.communicate.side_effect = delayed_communicate
    # kill is a sync method, so we need a MagicMock, not AsyncMock default
    process_mock.kill = MagicMock()
    # wait is an async method, AsyncMock is correct
    process_mock.wait = AsyncMock()

    with patch(
        "asyncio.create_subprocess_shell", return_value=process_mock
    ) as mock_shell:
        exit_code = await runner.run()

        assert exit_code == 124  # Timeout exit code
        process_mock.kill.assert_called_once()


@pytest.mark.asyncio
async def test_run_interactive(local_config, mock_console):
    local_config.mode = "interactive"
    runner = LocalRunner(local_config, mock_console)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        exit_code = await runner.run()

        assert exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == "echo test"
        assert kwargs["shell"] is True


@pytest.mark.asyncio
async def test_run_with_error_context(local_config, mock_console):
    runner = LocalRunner(local_config, mock_console)
    error_context = "Something went wrong"

    process_mock = AsyncMock()
    process_mock.communicate.return_value = (b"", b"")
    process_mock.returncode = 0

    with patch(
        "asyncio.create_subprocess_shell", return_value=process_mock
    ) as mock_shell:
        await runner.run(error_context=error_context)

        args, kwargs = mock_shell.call_args
        env = kwargs["env"]
        assert env["TEST_ERROR_CTX"] == "Something went wrong"
