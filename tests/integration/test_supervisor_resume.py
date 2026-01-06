import asyncio
import os
import signal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from git import Repo
from typer.testing import CliRunner

from veridical.api.models import SessionState
from veridical.cli.main import app
from veridical.models.result import PatchResult, PatchStatus, VerificationResult
from veridical.supervisor.loop import Supervisor
from veridical.supervisor.state_model import LoopState

runner = CliRunner()


@pytest.fixture(autouse=True)
def git_repo(tmp_path: Path) -> Repo:
    """Initialize a git repository for tests."""
    repo = Repo.init(tmp_path)
    repo.git.branch("-m", "main")
    (tmp_path / "README.md").write_text("Initial commit")
    repo.git.add(A=True)
    repo.git.commit("-m", "Initial commit")
    repo.create_remote("origin", "https://github.com/example/repo.git")
    return repo


def test_supervisor_interruption_and_resume(tmp_path: Path) -> None:
    """Verify that the supervisor saves state on interruption and can resume."""
    os.environ["JULES_API_KEY"] = "test_key"

    original_init = Supervisor.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        asyncio.create_task(interrupt_and_stop(self))

    async def interrupt_and_stop(supervisor: Supervisor):
        await asyncio.sleep(0.05)
        supervisor._handle_signal(signal.SIGINT)

    with patch(
        "veridical.supervisor.loop.Supervisor.__init__",
        side_effect=patched_init,
        autospec=True,
    ), patch(
        "veridical.dispatcher.session.Dispatcher.create_session", new_callable=AsyncMock
    ) as mock_create_session, patch(
        "pathlib.Path.cwd", return_value=tmp_path
    ):
        mock_create_session.return_value = MagicMock(session_id="mock_session")
        result = runner.invoke(
            app, ["run", "test task", "--no-spec"], catch_exceptions=False
        )

    assert "Shutdown requested" in result.stdout, result.stdout
    state_file = tmp_path / ".veridical_state.json"
    assert state_file.exists()

    state = LoopState.load(tmp_path)
    assert state is not None
    assert state.iteration == 1


def test_supervisor_resumes_from_state_file(tmp_path: Path) -> None:
    """Verify that the resume command loads state and calls the supervisor."""
    os.environ["JULES_API_KEY"] = "test_key"

    # Create a mock state file
    state = LoopState(
        iteration=2,
        session_id="resumed_session",
        error_context="old_error",
        work_branch="resumed-branch",
    )
    state.save(tmp_path)

    with patch("veridical.cli.run.run_supervisor") as mock_run_supervisor, patch(
        "pathlib.Path.cwd", return_value=tmp_path
    ):
        result = runner.invoke(app, ["resume"], catch_exceptions=False)

    assert result.exit_code == 0, result.stdout
    mock_run_supervisor.assert_called_once()
    call_kwargs = mock_run_supervisor.call_args.kwargs
    assert call_kwargs["session_id"] == "resumed_session"


@patch("veridical.supervisor.loop.Dispatcher", autospec=True)
@patch("veridical.supervisor.loop.Poller", autospec=True)
@patch("veridical.supervisor.loop.Synchronizer", autospec=True)
@patch("veridical.supervisor.loop.Verifier", autospec=True)
def test_state_file_cleanup_on_success(
    MockVerifier, MockSynchronizer, MockPoller, MockDispatcher, tmp_path: Path
) -> None:
    """Verify that the state file is cleaned up on successful completion."""
    os.environ["JULES_API_KEY"] = "test_key"
    state_file = tmp_path / ".veridical_state.json"

    LoopState(
        iteration=1,
        session_id="test",
        error_context="test",
        work_branch="test",
    ).save(tmp_path)
    assert state_file.exists()

    mock_dispatcher_instance = MockDispatcher.return_value
    mock_poller_instance = MockPoller.return_value
    mock_synchronizer_instance = MockSynchronizer.return_value
    mock_verifier_instance = MockVerifier.return_value
    mock_synchronizer_instance.work_branch = "test-success-branch"
    mock_dispatcher_instance.create_session = AsyncMock(
        return_value=MagicMock(session_id="mock_session")
    )
    mock_poller_instance.wait_for_completion = AsyncMock(
        return_value=MagicMock(final_state=SessionState.COMPLETED)
    )
    mock_synchronizer_instance.apply_session_patch = AsyncMock(
        return_value=PatchResult(
            success=True, diff_hash="hash123", status=PatchStatus.APPLIED
        )
    )
    mock_verifier_instance.run_all = AsyncMock(
        return_value=VerificationResult(passed=True, results=[], duration_seconds=1.23)
    )
    mock_synchronizer_instance.merge_to_main = MagicMock(return_value="commit123")

    with patch("pathlib.Path.cwd", return_value=tmp_path):
        result = runner.invoke(
            app,
            ["run", "test task", "--force-new", "--no-spec"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0, result.stdout
    assert "SUCCESS" in result.stdout
    assert not state_file.exists()
