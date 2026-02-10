"""E2E tests for state persistence and resume logic."""

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


@pytest.mark.e2e
class TestResumePersistenceE2E:
    """End-to-end tests for resume logic (Task 4.3)."""

    @pytest.mark.asyncio
    async def test_resumed_session_continues_iteration_count(self, e2e_temp_repo, e2e_config):
        """Test: resumed session continues from saved iteration count (Task 4.3)."""
        # Max iterations is 5
        e2e_config.supervisor.max_iterations = 5

        # Mock worker
        worker = AsyncMock()
        worker.synchronizer = MagicMock()
        worker.synchronizer.setup_work_branch = MagicMock()
        worker.synchronizer.work_branch = "feat/test"

        # Mock synchronous return values to fail verification
        worker.dispatch.return_value = WorkResult(
            handle=WorkHandle(backend="jules", handle_data={"session_id": "sess-1"})
        )
        worker.poll.return_value = PollResult(status=WorkStatus.COMPLETED)
        worker.sync.return_value = SyncResult(success=True, iter_branch="iter-5", diff_hash="h5")

        supervisor = Supervisor(e2e_config, worker, e2e_temp_repo)

        # Create state file with iteration 5 about to run
        state_file = e2e_temp_repo / ".veridical_state.json"
        state = LoopState(
            task_description="test task",
            iteration=5,
            session_id="sess-1",
            work_branch="feat/test",
            started_at_timestamp=100.0,
        )
        state.save(state_file)

        # Mock verifier to fail so it tries to iterate
        supervisor.verifier = AsyncMock()
        supervisor.verifier.run_all.return_value = MagicMock(passed=False)
        supervisor.verifier.generate_feedback = AsyncMock(return_value="Fail")

        # Run - it should start at iteration 5
        result = await supervisor.run("test task", resume_from_state=True)

        # Supervisor.run reports iteration_count as is when tripping.
        # Iteration 5 runs. record_iteration(6) trips. count=6.
        assert result.iterations == 6
        assert "Maximum iterations exceeded" in result.failure_reason
