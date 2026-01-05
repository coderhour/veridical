"""Integration tests for the Supervisor loop."""

import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from veridical.supervisor.loop import Supervisor


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a git repo in a temporary directory."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )
    (tmp_path / "README.md").write_text("initial commit")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=tmp_path, check=True)
    return tmp_path


@pytest.mark.asyncio
async def test_supervisor_initializes_progress_reporter(git_repo: Path) -> None:
    """Test that the Supervisor initializes the ProgressReporter."""
    config = MagicMock()
    config.jules.backoff.type = "constant"
    config.jules.backoff.interval = 0.1
    client = MagicMock()

    supervisor = Supervisor(config, client, git_repo, verbose=True)

    assert supervisor.progress is not None
    assert supervisor.progress.verbose is True
    assert supervisor.poller.progress == supervisor.progress


@pytest.mark.asyncio
@patch("veridical.poller.monitor.Poller.wait_for_completion")
@patch("veridical.dispatcher.session.Dispatcher.create_session")
@patch("veridical.synchronizer.patch.Synchronizer.apply_session_patch")
@patch("veridical.verifier.quality_gate.Verifier.run_all")
@patch("sys.stdout")
@patch("sys.stderr")
@patch("time.sleep", return_value=None)
@patch("veridical.synchronizer.branch.BranchManager.__init__", return_value=None)
async def test_supervisor_run_updates_progress(
    mock_branch_manager_init: MagicMock,
    mock_sleep: MagicMock,
    mock_stderr: MagicMock,
    mock_stdout: MagicMock,
    mock_verifier_run: AsyncMock,
    mock_apply_patch: AsyncMock,
    mock_create_session: AsyncMock,
    mock_wait_for_completion: AsyncMock,
    git_repo: Path,
) -> None:
    """Test that the supervisor run loop updates the progress reporter."""
    # Mocks
    config = MagicMock(name="config")
    # Explicitly build the mock config to avoid issues with nested MagicMock
    # attributes not being set as expected.
    supervisor_config = MagicMock(name="supervisor_config")
    supervisor_config.max_iterations = 2
    supervisor_config.stagnation_threshold = 3
    supervisor_config.max_consecutive_failures = 5
    config.supervisor = supervisor_config
    feedback_config = MagicMock(name="feedback_config")
    feedback_config.max_length = 4096
    verifier_config = MagicMock(name="verifier_config")
    verifier_config.feedback = feedback_config
    verifier_config.summary_max_length = 4096
    verifier_config.local_llm = None
    config.verifier = verifier_config
    config.log_analyzer = None
    backoff_config = MagicMock(name="backoff_config")
    backoff_config.type = "constant"
    backoff_config.interval = 0.1
    jules_config = MagicMock(name="jules_config")
    jules_config.backoff = backoff_config
    config.jules = jules_config
    client = AsyncMock()
    # Mock return values
    mock_create_session.return_value = MagicMock(session_id="test_session")
    mock_wait_for_completion.return_value = MagicMock(
        final_state="COMPLETED",
    )
    mock_apply_patch.return_value = MagicMock(success=True, diff_hash="hash")
    # Ensure the verifier returns a result with failed gates to trigger feedback generation
    gate_result = MagicMock()
    gate_result.name = "test-gate"
    gate_result.exit_code = 1
    gate_result.output = "test output"
    gate_result.error_output = "test error output"
    mock_verifier_run.return_value = MagicMock(
        passed=False, failed_gates=[gate_result]
    )
    # Supervisor and mock progress reporter
    supervisor = Supervisor(config, client, git_repo, verbose=True)
    supervisor.synchronizer.branch_manager.base_branch = "master"
    supervisor.synchronizer.branch_manager.git = supervisor.synchronizer.git
    supervisor.synchronizer.branch_manager.branch_prefix = "test-iteration-"
    supervisor.synchronizer.branch_manager.starting_branch = "master"
    mock_progress = MagicMock()
    supervisor.progress = mock_progress
    supervisor.poller.progress = mock_progress

    # Run the loop
    await supervisor.run("test task")

    # Assertions
    assert mock_progress.set_state.call_count > 0
    mock_progress.set_state.assert_any_call("Creating session...")
    mock_progress.set_state.assert_any_call("Polling for updates...")
    mock_progress.set_state.assert_any_call("Applying patch...")
    mock_progress.set_state.assert_any_call("Running quality gates...")
    mock_progress.set_state.assert_any_call("Sending feedback...")

    # Check iteration updates
    mock_progress.set_iterations.assert_any_call(1, 2)
    mock_progress.set_iterations.assert_any_call(2, 2)
