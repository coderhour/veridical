"""Integration tests for the Supervisor loop.

Updated to use the Worker protocol abstraction.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from veridical.models.result import VerificationResult
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


def _make_mock_worker() -> AsyncMock:
    """Create a mock worker with a mock synchronizer."""
    worker = AsyncMock()
    sync = MagicMock()
    sync.starting_branch = "main"
    sync.work_branch = "feat/fix-bug"
    sync._work_branch = "feat/fix-bug"
    sync.setup_work_branch = MagicMock()
    sync.merge_to_main = MagicMock(return_value="new_commit_hash")
    sync.cleanup_branch = MagicMock()
    sync.git = MagicMock()
    sync.patch_applier = MagicMock()
    worker.synchronizer = sync
    worker.progress = MagicMock()
    worker.dispatcher = MagicMock()
    return worker


@pytest.mark.asyncio
async def test_supervisor_one_shot_success(tmp_path) -> None:
    config = MagicMock()
    config.supervisor.max_iterations = 5
    config.supervisor.max_consecutive_failures = 3
    config.supervisor.stagnation_threshold = 3
    config.worklog.enabled = False

    worker = _make_mock_worker()
    worker.dispatch.return_value = WorkResult(
        handle=_make_handle("sess_1", prompt="prompt"),
    )
    worker.poll.return_value = PollResult(status=WorkStatus.COMPLETED)
    worker.sync.return_value = SyncResult(success=True, iter_branch="iter-1", diff_hash="hash1")

    supervisor = Supervisor(config, worker, tmp_path)

    verify_res = VerificationResult(passed=True, gates=[], duration_seconds=1.0)
    with patch.object(supervisor.verifier, "run_all", AsyncMock(return_value=verify_res)):
        result = await supervisor.run("Fix bug")

    assert result.success
    assert result.iterations == 1
    assert result.final_commit == "new_commit_hash"

    worker.dispatch.assert_called_once()
    worker.poll.assert_called_once()
    worker.sync.assert_called_once()


@pytest.mark.asyncio
async def test_supervisor_iterative_repair(tmp_path) -> None:
    config = MagicMock()
    config.supervisor.max_iterations = 5
    config.supervisor.max_consecutive_failures = 3
    config.supervisor.stagnation_threshold = 3
    config.worklog.enabled = False

    worker = _make_mock_worker()

    # Iteration 1: dispatch → poll → sync → verify (fail)
    # Iteration 2: dispatch → poll → sync → verify (pass)
    worker.dispatch.side_effect = [
        WorkResult(handle=_make_handle("sess_1", prompt="p1")),
        WorkResult(handle=_make_handle("sess_1")),
    ]
    worker.poll.side_effect = [
        PollResult(status=WorkStatus.COMPLETED),
        PollResult(status=WorkStatus.COMPLETED),
    ]
    worker.sync.side_effect = [
        SyncResult(success=True, iter_branch="iter-1", diff_hash="hash1"),
        SyncResult(success=True, iter_branch="iter-2", diff_hash="hash2"),
    ]

    supervisor = Supervisor(config, worker, tmp_path)

    fail_res = VerificationResult(passed=False, gates=[], duration_seconds=1.0)
    pass_res = VerificationResult(passed=True, gates=[], duration_seconds=1.0)

    with (
        patch.object(
            supervisor.verifier,
            "run_all",
            side_effect=[fail_res, pass_res],
        ),
        patch.object(supervisor.verifier, "generate_feedback", return_value="Error info"),
    ):
        result = await supervisor.run("Fix bug")

    assert result.success
    assert result.iterations == 2

    # Worker.dispatch called twice (once per iteration)
    assert worker.dispatch.call_count == 2

    # Second dispatch should include error_context from verification failure
    second_call = worker.dispatch.call_args_list[1]
    assert second_call[0][1] == "Error info"  # error_context positional arg


@pytest.mark.asyncio
async def test_supervisor_circuit_breaker(tmp_path) -> None:
    config = MagicMock()
    config.supervisor.max_iterations = 2
    config.supervisor.max_consecutive_failures = 3
    config.supervisor.stagnation_threshold = 3
    config.worklog.enabled = False

    worker = _make_mock_worker()

    # 3 iterations worth of data (circuit breaker trips after iteration 3 starts)
    worker.dispatch.side_effect = [
        WorkResult(handle=_make_handle("sess_1", prompt="p1")),
        WorkResult(handle=_make_handle("sess_1")),
        WorkResult(handle=_make_handle("sess_1")),
    ]
    worker.poll.side_effect = [
        PollResult(status=WorkStatus.COMPLETED),
        PollResult(status=WorkStatus.COMPLETED),
        PollResult(status=WorkStatus.COMPLETED),
    ]
    worker.sync.side_effect = [
        SyncResult(success=True, iter_branch="iter-1", diff_hash="hash1"),
        SyncResult(success=True, iter_branch="iter-2", diff_hash="hash2"),
        SyncResult(success=True, iter_branch="iter-3", diff_hash="hash3"),
    ]

    supervisor = Supervisor(config, worker, tmp_path)

    fail_res = VerificationResult(passed=False, gates=[], duration_seconds=1.0)

    with (
        patch.object(supervisor.verifier, "run_all", AsyncMock(return_value=fail_res)),
        patch.object(supervisor.verifier, "generate_feedback", AsyncMock(return_value="Error")),
    ):
        result = await supervisor.run("Task")

    assert not result.success
    # With max_iterations=2, iterations 1 and 2 run, then circuit breaker
    # opens before iteration 3 can start (check happens after record_iteration)
    assert result.iterations == 3
    assert "Maximum iterations" in result.failure_reason
