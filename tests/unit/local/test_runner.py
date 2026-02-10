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


# ---------------------------------------------------------------------------
# Provider-aware runner tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_with_provider_delegates_command(config, console):
    """When a provider is set, runner uses provider.build_command()."""
    config.worker_command = ""  # No explicit command

    provider = MagicMock()
    provider.default_mode.return_value = "subprocess"
    provider.build_command.return_value = "claude --print -p 'Fix it'"

    runner = LocalRunner(config, console, provider=provider)

    with patch("asyncio.create_subprocess_shell", new_callable=MagicMock) as mock_shell:
        process_mock = MagicMock()
        process_mock.communicate = MagicMock(
            side_effect=lambda: asyncio.sleep(0, result=(b"", b""))
        )
        process_mock.returncode = 0

        future = asyncio.Future()
        future.set_result(process_mock)
        mock_shell.return_value = future

        exit_code = await runner.run(task="Fix it")

        assert exit_code == 0
        provider.build_command.assert_called_once_with("Fix it", None, mode="subprocess")
        args, _ = mock_shell.call_args
        assert args[0] == "claude --print -p 'Fix it'"


@pytest.mark.asyncio
async def test_run_with_provider_passes_error_context(config, console):
    """Provider receives error_context when available."""
    config.worker_command = ""

    provider = MagicMock()
    provider.default_mode.return_value = "subprocess"
    provider.build_command.return_value = "claude --print -p 'Fix it'"

    runner = LocalRunner(config, console, provider=provider)

    with patch("asyncio.create_subprocess_shell", new_callable=MagicMock) as mock_shell:
        process_mock = MagicMock()
        process_mock.communicate = MagicMock(
            side_effect=lambda: asyncio.sleep(0, result=(b"", b""))
        )
        process_mock.returncode = 0

        future = asyncio.Future()
        future.set_result(process_mock)
        mock_shell.return_value = future

        await runner.run(error_context="tests failed", task="Fix it")

        provider.build_command.assert_called_once_with("Fix it", "tests failed", mode="subprocess")


@pytest.mark.asyncio
async def test_run_with_provider_uses_provider_default_mode(config, console):
    """When worker_command is empty, runner uses provider.default_mode()."""
    config.worker_command = ""
    config.mode = "subprocess"  # Config says subprocess

    provider = MagicMock()
    provider.default_mode.return_value = "interactive"  # Provider says interactive
    provider.build_command.return_value = "claude"

    runner = LocalRunner(config, console, provider=provider)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        exit_code = await runner.run(task="Fix it")

        assert exit_code == 0
        # Should use interactive mode (from provider), not subprocess (from config)
        mock_run.assert_called_once()
        provider.build_command.assert_called_once_with("Fix it", None, mode="interactive")


@pytest.mark.asyncio
async def test_run_without_provider_backward_compat(config, console):
    """Without a provider, runner uses config.worker_command as before."""
    runner = LocalRunner(config, console)  # No provider

    with patch("asyncio.create_subprocess_shell", new_callable=MagicMock) as mock_shell:
        process_mock = MagicMock()
        process_mock.communicate = MagicMock(
            side_effect=lambda: asyncio.sleep(0, result=(b"", b""))
        )
        process_mock.returncode = 0

        future = asyncio.Future()
        future.set_result(process_mock)
        mock_shell.return_value = future

        exit_code = await runner.run()

        assert exit_code == 0
        args, _ = mock_shell.call_args
        assert args[0] == "echo hello"


# ---------------------------------------------------------------------------
# gtr worktree-wrapped runner tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_with_worktree_branch_wraps_command(config, console):
    """When worktree_branch is set, command is wrapped with git gtr run."""
    runner = LocalRunner(config, console, worktree_branch="veri/my-feature")

    with patch("asyncio.create_subprocess_shell", new_callable=MagicMock) as mock_shell:
        process_mock = MagicMock()
        process_mock.communicate = MagicMock(
            side_effect=lambda: asyncio.sleep(0, result=(b"", b""))
        )
        process_mock.returncode = 0

        future = asyncio.Future()
        future.set_result(process_mock)
        mock_shell.return_value = future

        exit_code = await runner.run()

        assert exit_code == 0
        args, _ = mock_shell.call_args
        assert args[0] == "git gtr run veri/my-feature echo hello"


@pytest.mark.asyncio
async def test_run_with_worktree_branch_and_provider(config, console):
    """gtr wrapping works together with provider command construction."""
    config.worker_command = ""

    provider = MagicMock()
    provider.default_mode.return_value = "subprocess"
    provider.build_command.return_value = "claude --print -p 'Fix it'"

    runner = LocalRunner(config, console, provider=provider, worktree_branch="veri/fix-bug")

    with patch("asyncio.create_subprocess_shell", new_callable=MagicMock) as mock_shell:
        process_mock = MagicMock()
        process_mock.communicate = MagicMock(
            side_effect=lambda: asyncio.sleep(0, result=(b"", b""))
        )
        process_mock.returncode = 0

        future = asyncio.Future()
        future.set_result(process_mock)
        mock_shell.return_value = future

        exit_code = await runner.run(task="Fix it")

        assert exit_code == 0
        args, _ = mock_shell.call_args
        assert args[0] == "git gtr run veri/fix-bug claude --print -p 'Fix it'"


@pytest.mark.asyncio
async def test_run_without_worktree_branch_no_wrapping(config, console):
    """Without worktree_branch, command is not wrapped."""
    runner = LocalRunner(config, console, worktree_branch=None)

    with patch("asyncio.create_subprocess_shell", new_callable=MagicMock) as mock_shell:
        process_mock = MagicMock()
        process_mock.communicate = MagicMock(
            side_effect=lambda: asyncio.sleep(0, result=(b"", b""))
        )
        process_mock.returncode = 0

        future = asyncio.Future()
        future.set_result(process_mock)
        mock_shell.return_value = future

        exit_code = await runner.run()

        assert exit_code == 0
        args, _ = mock_shell.call_args
        assert args[0] == "echo hello"
