"""Tests for supervisor session resume functionality.

Updated to use the Worker protocol abstraction.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from veridical.config.schema import (
    GitConfig,
    JulesConfig,
    SupervisorConfig,
    VeridicalConfig,
    VerifierConfig,
)
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
    """Create a WorkHandle with a session_id."""
    return WorkHandle(backend="jules", handle_data={"session_id": session_id, **extra})


@pytest.mark.unit
class TestSupervisorSessionResume:
    """Tests for session resume functionality in Supervisor."""

    @pytest.fixture
    def mock_config(self) -> VeridicalConfig:
        """Create a test config."""
        return VeridicalConfig(
            jules=JulesConfig(),
            supervisor=SupervisorConfig(
                max_iterations=10,
                max_consecutive_failures=3,
                stagnation_threshold=3,
            ),
            verifier=VerifierConfig(quality_gates=[]),
            git=GitConfig(),
        )

    @pytest.fixture
    def mock_synchronizer(self) -> MagicMock:
        """Create a mock synchronizer for branch management."""
        sync = MagicMock()
        sync.starting_branch = "main"
        sync.work_branch = "feat/test-task"
        sync._work_branch = "feat/test-task"
        sync.setup_work_branch = MagicMock()
        sync.merge_to_main = MagicMock(return_value="commit123")
        sync.cleanup_branch = MagicMock()
        sync.git = MagicMock()
        sync.patch_applier = MagicMock()
        return sync

    @pytest.fixture
    def mock_worker(self, mock_synchronizer: MagicMock) -> AsyncMock:
        """Create a mock worker implementing the Worker protocol."""
        worker = AsyncMock()
        worker.synchronizer = mock_synchronizer
        worker.progress = MagicMock()
        worker.dispatcher = MagicMock()
        return worker

    @pytest.fixture
    def supervisor(
        self,
        mock_config: VeridicalConfig,
        mock_worker: AsyncMock,
        tmp_path: Path,
    ) -> Supervisor:
        """Create a supervisor instance with mocked worker."""
        sup = Supervisor(mock_config, mock_worker, tmp_path)
        return sup

    @pytest.mark.asyncio
    async def test_run_with_session_id_skips_dispatching(self, supervisor: Supervisor) -> None:
        """Test that providing session_id skips dispatching on first iteration."""
        worker = supervisor.worker

        # Worker.dispatch returns a handle with resumed=True (no new session created)
        worker.dispatch.return_value = WorkResult(
            handle=_make_handle("existing-session-123", resumed=True),
        )
        worker.poll.return_value = PollResult(status=WorkStatus.COMPLETED)
        worker.sync.return_value = SyncResult(
            success=True, iter_branch="test-branch", diff_hash="abc123"
        )

        verification_result = VerificationResult(passed=True, gates=[], duration_seconds=1.0)
        with patch.object(supervisor.verifier, "run_all", return_value=verification_result):
            result = await supervisor.run("Test task", session_id="existing-session-123")

        # Worker.dispatch was called with session_id (resume path)
        worker.dispatch.assert_called_once()
        call_kwargs = worker.dispatch.call_args
        assert call_kwargs.kwargs.get("session_id") == "existing-session-123"
        assert call_kwargs.kwargs.get("iteration") == 1

        assert result.success
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_run_without_session_id_creates_new_session(self, supervisor: Supervisor) -> None:
        """Test that normal flow creates a new session when no session_id provided."""
        worker = supervisor.worker

        worker.dispatch.return_value = WorkResult(
            handle=_make_handle("new-session-456", prompt="Build prompt"),
        )
        worker.poll.return_value = PollResult(status=WorkStatus.COMPLETED)
        worker.sync.return_value = SyncResult(
            success=True, iter_branch="test-branch", diff_hash="abc123"
        )

        verification_result = VerificationResult(passed=True, gates=[], duration_seconds=1.0)
        with patch.object(supervisor.verifier, "run_all", return_value=verification_result):
            result = await supervisor.run("Test task")

        # Worker.dispatch was called without session_id
        worker.dispatch.assert_called_once()
        call_kwargs = worker.dispatch.call_args
        assert call_kwargs.kwargs.get("session_id") is None

        assert result.success
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_resume_then_iterate_sends_feedback_to_same_session(
        self, supervisor: Supervisor
    ) -> None:
        """Test that subsequent iterations send feedback to the same session instead of creating new ones."""
        worker = supervisor.worker

        # Iteration 1: resume existing session
        # Iteration 2: send feedback to same session
        worker.dispatch.side_effect = [
            WorkResult(handle=_make_handle("existing-session-123", resumed=True)),
            WorkResult(handle=_make_handle("existing-session-123")),
        ]
        worker.poll.side_effect = [
            PollResult(status=WorkStatus.COMPLETED),
            PollResult(status=WorkStatus.COMPLETED),
        ]
        worker.sync.side_effect = [
            SyncResult(success=True, iter_branch="test-branch-1", diff_hash="abc123"),
            SyncResult(success=True, iter_branch="test-branch-2", diff_hash="def456"),
        ]

        verification_fail = VerificationResult(passed=False, gates=[], duration_seconds=1.0)
        verification_pass = VerificationResult(passed=True, gates=[], duration_seconds=1.0)

        with (
            patch.object(
                supervisor.verifier,
                "run_all",
                side_effect=[verification_fail, verification_pass],
            ),
            patch.object(supervisor.verifier, "generate_feedback", return_value="Test failed"),
        ):
            result = await supervisor.run("Test task", session_id="existing-session-123")

        # Worker.dispatch called twice (once per iteration)
        assert worker.dispatch.call_count == 2

        # Second call should have session_id and iteration=2
        second_call = worker.dispatch.call_args_list[1]
        assert second_call.kwargs.get("session_id") == "existing-session-123"
        assert second_call.kwargs.get("iteration") == 2

        assert result.success
        assert result.iterations == 2

    @pytest.mark.asyncio
    async def test_resume_with_invalid_session_fails_gracefully(
        self, supervisor: Supervisor
    ) -> None:
        """Test that invalid session ID fails gracefully with clear message."""
        worker = supervisor.worker

        worker.dispatch.return_value = WorkResult(
            handle=_make_handle("invalid-session-999", resumed=True),
        )
        # Poll returns failure with "could not be found" message
        worker.poll.return_value = PollResult(
            status=WorkStatus.FAILED,
            error="The session 'invalid-session-999' could not be found.",
        )

        result = await supervisor.run("Test task", session_id="invalid-session-999")

        assert not result.success
        assert "could not be found" in (result.failure_reason or "")
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_resume_with_timeout_fails_gracefully(self, supervisor: Supervisor) -> None:
        """Test that timeout during resume fails gracefully."""
        worker = supervisor.worker

        worker.dispatch.return_value = WorkResult(
            handle=_make_handle("slow-session-123", resumed=True),
        )
        worker.poll.return_value = PollResult(
            status=WorkStatus.FAILED,
            error="Session timed out",
        )

        result = await supervisor.run("Test task", session_id="slow-session-123")

        assert not result.success
        assert "timed out" in (result.failure_reason or "")
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_resume_patch_failure_aborts_immediately(self, supervisor: Supervisor) -> None:
        """Test that patch failure on resumed session aborts instead of retrying."""
        worker = supervisor.worker

        worker.dispatch.return_value = WorkResult(
            handle=_make_handle("existing-session-123", resumed=True),
        )
        worker.poll.return_value = PollResult(status=WorkStatus.COMPLETED)
        worker.sync.return_value = SyncResult(
            success=False,
            iter_branch="test-branch",
            error="patch failed: README.md: patch does not apply",
        )

        result = await supervisor.run("Test task", session_id="existing-session-123")

        # Verify failure — patch failures are not recoverable
        assert not result.success
        assert result.failure_reason == "Patch failed to apply"
        assert result.iterations == 1
