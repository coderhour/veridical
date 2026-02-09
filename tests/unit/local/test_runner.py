import asyncio
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from veridical.config.schema import LocalConfig
from veridical.local.runner import LocalRunner


@pytest.fixture
def console():
    return MagicMock(spec=Console)


@pytest.fixture
def config():
    return LocalConfig(
        worker_command="echo hello",
        worker_timeout=10,
        mode="subprocess",
        error_env_var="TEST_ERROR",
    )


@pytest.mark.asyncio
async def test_run_subprocess_success(config, console):
    runner = LocalRunner(config, console)

    # Patch create_subprocess_shell
    process_mock = MagicMock()
    process_mock.communicate.return_value = (b"hello\n", b"")
    process_mock.returncode = 0

    with patch("asyncio.create_subprocess_shell", new_callable=MagicMock) as mock_shell:
        # Make the mock return an awaitable that yields the process_mock
        future = asyncio.Future()
        future.set_result(process_mock)
        mock_shell.return_value = future

        # We need to mock awaitable communicate
        process_mock.communicate = MagicMock(
            side_effect=lambda: asyncio.sleep(0, result=(b"hello\n", b""))
        )

        exit_code = await runner.run()

        assert exit_code == 0
        mock_shell.assert_called_once()
        args, kwargs = mock_shell.call_args
        assert args[0] == "echo hello"
        assert kwargs["stdout"] == asyncio.subprocess.PIPE
        assert kwargs["stderr"] == asyncio.subprocess.PIPE


@pytest.mark.asyncio
async def test_run_interactive(config, console):
    config.mode = "interactive"
    runner = LocalRunner(config, console)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        exit_code = await runner.run()

        assert exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == "echo hello"
        assert kwargs["shell"] is True


@pytest.mark.asyncio
async def test_error_context_passing(config, console):
    config.mode = "subprocess"
    runner = LocalRunner(config, console)
    error_context = "Something went wrong"

    with patch("asyncio.create_subprocess_shell", new_callable=MagicMock) as mock_shell:
        process_mock = MagicMock()
        process_mock.communicate = MagicMock(
            side_effect=lambda: asyncio.sleep(0, result=(b"", b""))
        )
        process_mock.returncode = 0

        future = asyncio.Future()
        future.set_result(process_mock)
        mock_shell.return_value = future

        await runner.run(error_context=error_context)

        mock_shell.assert_called_once()
        _, kwargs = mock_shell.call_args
        env = kwargs["env"]
        assert env["TEST_ERROR"] == error_context


@pytest.mark.asyncio
async def test_missing_command(config, console):
    config.worker_command = ""
    runner = LocalRunner(config, console)

    exit_code = await runner.run()

    assert exit_code == 1
    console.print.assert_called_with("[bold red]Error:[/bold red] No worker command specified.")
