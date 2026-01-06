"""Integration tests for the Supervisor loop."""

import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from veridical.supervisor.loop import Supervisor
from veridical.models.result import VerificationResult, GateResult, GateStatus, PatchResult
from veridical.api.models import SessionResponse, SessionState

@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a git repo in a temporary directory."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("initial commit")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=tmp_path, check=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=tmp_path, check=True)
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
async def test_supervisor_run_updates_progress(git_repo: Path, mocker) -> None:
    """Test that the supervisor run loop updates the progress reporter."""
    config = MagicMock()
    config.supervisor.max_iterations = 2
    config.supervisor.max_consecutive_failures = 3
    config.supervisor.stagnation_threshold = 3
    config.jules.backoff.type = "constant"
    config.git.base_branch = "main"
    config.git.branch_prefix = "veridical/iter-"
    config.jules.backoff.interval = 0.1
    client = AsyncMock()

    mocker.patch("veridical.dispatcher.session.Dispatcher.create_session", return_value=SessionResponse(name="sessions/test_session"))
    mocker.patch("veridical.poller.monitor.Poller.wait_for_completion", return_value=MagicMock(final_state=SessionState.COMPLETED))
    mocker.patch("veridical.synchronizer.patch.Synchronizer.apply_session_patch", return_value=PatchResult(success=True, diff_hash="hash", status="applied", files_changed=[]))

    gate_result = GateResult(name="test-gate", status=GateStatus.FAILED, duration_seconds=1.0)
    mocker.patch("veridical.verifier.quality_gate.Verifier.run_all", return_value=VerificationResult(passed=False, gates=[gate_result], duration_seconds=1.0))
    mocker.patch("veridical.verifier.feedback.FeedbackGenerator.generate_feedback", return_value="Test feedback")

    supervisor = Supervisor(config, client, git_repo, verbose=True)
    mock_progress = MagicMock()
    supervisor.progress = mock_progress
    supervisor.poller.progress = mock_progress

    await supervisor.run(task_description="test task")

    assert mock_progress.set_state.call_count > 0
    mock_progress.set_state.assert_any_call("Creating session...")
    mock_progress.set_state.assert_any_call("Polling for updates...")
    mock_progress.set_state.assert_any_call("Applying patch...")
    mock_progress.set_state.assert_any_call("Running quality gates...")
    mock_progress.set_state.assert_any_call("Compiling feedback...")

    mock_progress.set_iterations.assert_any_call(1, 2)
    mock_progress.set_iterations.assert_any_call(2, 2)
