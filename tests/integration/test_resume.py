from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from veridical.supervisor.loop import Supervisor
from veridical.supervisor.state import LoopState
from veridical.worker.jules import JulesWorker
from veridical.models.result import PatchResult, PatchStatus


@pytest.fixture(autouse=True)
def mock_logger():
    """Mock logger to prevent 'I/O operation on closed file' errors."""
    with patch("veridical.supervisor.loop.logger") as mock:
        yield mock

@pytest.mark.asyncio
async def test_supervisor_resume_loads_state(tmp_path: Path) -> None:
    """Test that supervisor loads state when resuming."""
    config = MagicMock()
    config.supervisor.max_iterations = 10
    config.supervisor.max_consecutive_failures = 3
    config.supervisor.stagnation_threshold = 3
    config.jules.backoff_strategy = "constant"
    config.jules.poll_interval = 0.1
    config.jules.poll_timeout = 5.0

    # Initialize git repo
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "Initial commit"], cwd=tmp_path, check=True
    )

    client = MagicMock()

    # Create worker
    with patch("veridical.worker.jules.Dispatcher"), \
         patch("veridical.worker.jules.Poller"), \
         patch("veridical.worker.jules.Synchronizer"):
        worker = JulesWorker(config, client, tmp_path)

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

    # Mock dependencies to avoid actual execution
    # Access via worker
    supervisor.worker.synchronizer = MagicMock()
    supervisor.worker.synchronizer.setup_work_branch = MagicMock()
    # Mock prepare as well since Supervisor calls it
    supervisor.worker.prepare = AsyncMock()

    # We want to exit loop immediately after setup
    # But run() sets circuit breaker count.
    # We can mock record_iteration to stop the loop or set _is_open
    supervisor.circuit_breaker.record_iteration = MagicMock()
    supervisor.circuit_breaker._is_open = True

    # Run
    await supervisor.run("resumed task", resume_from_state=True)

    # Verify prepare called
    supervisor.worker.prepare.assert_called()

    # Also verify circuit breaker iteration set correctly
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
    config.jules.backoff_strategy = "constant"
    config.jules.poll_interval = 0.1
    config.jules.poll_timeout = 5.0

    # Initialize git repo
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "Initial commit"], cwd=tmp_path, check=True
    )

    client = AsyncMock()  # client needs to be async for await calls

    # Create worker
    with patch("veridical.worker.jules.Dispatcher"), \
         patch("veridical.worker.jules.Poller"), \
         patch("veridical.worker.jules.Synchronizer"):
        worker = JulesWorker(config, client, tmp_path)

    supervisor = Supervisor(config, worker, tmp_path)

    # Create state file
    state_file = tmp_path / ".veridical_state.json"
    state_file.touch()

    # Mock mocks
    # verifier run_all returns success
    supervisor.verifier = AsyncMock()
    supervisor.verifier.run_all.return_value = MagicMock(passed=True)

    # Mock worker components
    worker.dispatcher = MagicMock()
    worker.dispatcher.build_prompt = MagicMock(return_value="prompt")
    worker.dispatcher.create_session = AsyncMock()
    worker.dispatcher.create_session.return_value = MagicMock(session_id="sess-1")

    worker.poller = AsyncMock()
    worker.poller.wait_for_completion.return_value = MagicMock(
        final_state="COMPLETED",
        duration_seconds=1.0
    )
    from veridical.api.models import SessionState
    worker.poller.wait_for_completion.return_value.final_state = SessionState.COMPLETED

    worker.synchronizer = MagicMock()
    worker.synchronizer.work_branch = "feat/new-task"
    worker.synchronizer.apply_session_patch = AsyncMock()

    # Use real PatchResult object
    patch_result = PatchResult(
        success=True,
        files_changed=["test.py"],
        diff_hash="abc",
        status=PatchStatus.APPLIED,
        patch_summary="summary"
    )

    worker.synchronizer.apply_session_patch.return_value = (
        "iter-1",
        patch_result
    )
    worker.synchronizer.merge_to_main = MagicMock(return_value="commit-hash")
    worker.synchronizer.git = MagicMock() # for cleanup

    # Run
    await supervisor.run("new task")

    # Verify state file deleted
    assert not state_file.exists()
