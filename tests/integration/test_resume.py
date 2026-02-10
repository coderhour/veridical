from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from veridical.supervisor.loop import Supervisor
from veridical.supervisor.state import LoopState
from veridical.worker.models import (
    PollResult,
    SyncResult,
    WorkHandle,
    WorkResult,
    WorkStatus,
)


def _make_handle(session_id: str, **extra: object) -> WorkHandle:
    return WorkHandle(backend="jules", handle_data={"session_id": session_id, **extra})


def _make_mock_worker() -> AsyncMock:
    """Create a mock worker with a mock synchronizer."""
    worker = AsyncMock()
    sync = MagicMock()
    sync.starting_branch = "main"
    sync.work_branch = "feat/test"
    sync._work_branch = "feat/test"
    sync.setup_work_branch = MagicMock()
    sync.merge_to_main = MagicMock(return_value="commit-hash")
    sync.cleanup_branch = MagicMock()
    sync.git = MagicMock()
    sync.patch_applier = MagicMock()
    worker.synchronizer = sync
    worker.progress = MagicMock()
    worker.dispatcher = MagicMock()
    return worker


@pytest.mark.asyncio
async def test_supervisor_resume_loads_state(tmp_path: Path) -> None:
    """Test that supervisor loads state when resuming."""
    config = MagicMock()
    config.supervisor.max_iterations = 10
    config.supervisor.max_consecutive_failures = 3
    config.supervisor.stagnation_threshold = 3
    config.worklog.enabled = False

    worker = _make_mock_worker()

    supervisor = Supervisor(config, worker, tmp_path)

    # Create state file
    state_file = tmp_path / ".veridical_state.json"
    state = LoopState(
        task_description="resumed task",
        iteration=5,
        session_id="sess-5",
        work_branch="feat/resumed",
        started_at_timestamp=1234.0,
    )
    state.save(state_file)

    # We want to exit loop immediately after setup
    supervisor.circuit_breaker.record_iteration = MagicMock()
    supervisor.circuit_breaker._is_open = True

    # Run
    await supervisor.run("resumed task", resume_from_state=True)

    # Verify setup_work_branch called with saved branch
    worker.synchronizer.setup_work_branch.assert_called_with("resumed task", "feat/resumed")

    # Verify circuit breaker iteration set correctly
    # state.iteration is 5. start_iteration = 5.
    # code: self._circuit_breaker._iteration_count = start_iteration - 1  => 4
    assert supervisor.circuit_breaker._iteration_count == 4


@pytest.mark.asyncio
async def test_supervisor_cleans_up_state_on_success(tmp_path: Path) -> None:
    """Test that state file is deleted on success."""
    config = MagicMock()
    config.supervisor.max_iterations = 10
    config.supervisor.max_consecutive_failures = 3
    config.supervisor.stagnation_threshold = 3
    config.worklog.enabled = False

    worker = _make_mock_worker()

    # Worker returns success flow
    worker.dispatch.return_value = WorkResult(
        handle=_make_handle("sess-1", prompt="Build prompt"),
    )
    worker.poll.return_value = PollResult(status=WorkStatus.COMPLETED)
    worker.sync.return_value = SyncResult(success=True, iter_branch="iter-1", diff_hash="abc")

    supervisor = Supervisor(config, worker, tmp_path)

    # Create state file
    state_file = tmp_path / ".veridical_state.json"
    state_file.touch()

    # verifier run_all returns success
    supervisor.verifier = AsyncMock()
    supervisor.verifier.run_all.return_value = MagicMock(passed=True)

    # Run
    await supervisor.run("new task")

    # Verify state file deleted
    assert not state_file.exists()
