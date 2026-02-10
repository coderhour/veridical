"""Integration tests for the Supervisor loop.

Updated to use the Worker protocol abstraction.
"""

import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from veridical.supervisor.loop import Supervisor
from veridical.worker.models import (
    PollResult,
    SyncResult,
    WorkHandle,
    WorkResult,
    WorkStatus,
)


def _make_handle(session_id: str, **extra: object) -> WorkHandle:
    return WorkHandle(backend="jules", handle_data={"session_id": session_id, **extra})


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a git repo in a temporary directory."""
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("initial commit")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=tmp_path, check=True)
    return tmp_path


@pytest.mark.asyncio
@pytest.mark.filterwarnings("ignore::ResourceWarning")
@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
async def test_supervisor_initializes_with_worker(git_repo: Path) -> None:
    """Test that the Supervisor initializes with a Worker instance."""
    config = MagicMock()
    config.supervisor.max_iterations = 10
    config.supervisor.max_consecutive_failures = 3
    config.supervisor.stagnation_threshold = 3
    config.worklog.enabled = False

    worker = AsyncMock()
    worker.synchronizer = MagicMock()
    worker.progress = MagicMock()

    supervisor = Supervisor(config, worker, git_repo, verbose=True)

    assert supervisor.worker is worker
    assert supervisor.verbose is True


@pytest.mark.asyncio
async def test_supervisor_run_calls_worker_methods(git_repo: Path) -> None:
    """Test that the supervisor run loop calls Worker protocol methods in order."""
    config = MagicMock(name="config")
    config.supervisor.max_iterations = 2
    config.supervisor.stagnation_threshold = 3
    config.supervisor.max_consecutive_failures = 5
    config.worklog.enabled = False

    worker = AsyncMock()
    sync = MagicMock()
    sync.starting_branch = "main"
    sync.work_branch = "main"
    sync._work_branch = "main"
    sync.setup_work_branch = MagicMock()
    sync.merge_to_main = MagicMock(return_value="commit123")
    sync.cleanup_branch = MagicMock()
    sync.git = MagicMock()
    sync.patch_applier = MagicMock()
    worker.synchronizer = sync
    worker.progress = MagicMock()
    worker.dispatcher = MagicMock()

    # Iteration 1: dispatch → poll → sync → verify (fail)
    # Iteration 2: dispatch → poll → sync → verify (pass)
    worker.dispatch.side_effect = [
        WorkResult(handle=_make_handle("sess-1", prompt="prompt1")),
        WorkResult(handle=_make_handle("sess-1")),
    ]
    worker.poll.side_effect = [
        PollResult(status=WorkStatus.COMPLETED),
        PollResult(status=WorkStatus.COMPLETED),
    ]
    worker.sync.side_effect = [
        SyncResult(success=True, iter_branch="iter-1", diff_hash="hash1"),
        SyncResult(success=True, iter_branch="iter-2", diff_hash="hash2"),
    ]

    supervisor = Supervisor(config, worker, git_repo, verbose=True)

    gate_result = MagicMock()
    gate_result.name = "test-gate"
    gate_result.exit_code = 1
    gate_result.output = "test output"
    gate_result.error_output = "test error output"

    with (
        patch.object(
            supervisor.verifier,
            "run_all",
            side_effect=[
                MagicMock(passed=False, failed_gates=[gate_result]),
                MagicMock(passed=True, gate_results=[]),
            ],
        ),
        patch.object(supervisor.verifier, "generate_feedback", return_value="Test failed"),
    ):
        result = await supervisor.run("test task")

    assert result.success
    assert result.iterations == 2
    assert worker.dispatch.call_count == 2
    assert worker.poll.call_count == 2
    assert worker.sync.call_count == 2
