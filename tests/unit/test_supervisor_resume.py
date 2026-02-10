"""Tests for supervisor session resume functionality."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from veridical.api.exceptions import APIError
from veridical.api.models import SessionState
from veridical.config.schema import (
    GitConfig,
    JulesConfig,
    SupervisorConfig,
    VeridicalConfig,
    VerifierConfig,
    WorkerConfig,
)
from veridical.models.result import VerificationResult, PatchResult
from veridical.supervisor.loop import Supervisor
from veridical.worker import WorkHandle, WorkResult, PollResult, SyncResult, Worker


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
            worker=WorkerConfig(),
        )

    @pytest.fixture
    def mock_worker(self) -> AsyncMock:
        """Create a mock Worker."""
        # Create a mock that satisfies Worker protocol and allows assertions
        worker = AsyncMock(spec=Worker)

        # Set default return values
        worker.prepare.return_value = "work-branch"
        worker.cleanup.return_value = None
        worker.finalize.return_value = "commit123"

        # We need these to return objects that match return type hints if checked,
        # but AsyncMock handles return values when awaited.

        return worker

    @pytest.fixture
    def supervisor(self, mock_config: VeridicalConfig, mock_worker: AsyncMock, tmp_path: Path) -> Supervisor:
        """Create a supervisor instance with mocked dependencies."""
        # Initialize git repo to prevent SynchronizationError if verifier checks git
        import subprocess

        # Use -q to reduce noise, ignore output
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "Initial", "-q"],
            cwd=tmp_path,
            check=True
        )

        sup = Supervisor(mock_config, mock_worker, tmp_path)

        # Mock verifier to avoid running real checks
        sup.verifier.run_all = AsyncMock(return_value=VerificationResult(
            passed=True, gates=[], duration_seconds=1.0
        ))
        sup.verifier.generate_feedback = AsyncMock(return_value="Feedback")

        return sup

    @pytest.mark.asyncio
    async def test_run_with_session_id_skips_dispatching(self, supervisor: Supervisor, mock_worker: AsyncMock) -> None:
        """Test that providing session_id skips dispatching on first iteration."""
        # Mock successful poll result
        poll_result = PollResult(
            handle=WorkHandle(id="existing-session-123"),
            status="completed",
            duration_seconds=1.0,
            error=None
        )
        mock_worker.poll.return_value = poll_result

        # Mock successful sync
        sync_result = SyncResult(
            patch_result=PatchResult.applied(files_changed=["test.py"], diff_hash="abc123"),
            branch_name="test-branch"
        )
        mock_worker.sync.return_value = sync_result

        result = await supervisor.run("Test task", session_id="existing-session-123")

        # Verify dispatcher (worker.dispatch) was NOT called on first iteration
        mock_worker.dispatch.assert_not_called()

        # Verify prepare was called
        mock_worker.prepare.assert_called_once()

        # Verify poll called with correct handle
        mock_worker.poll.assert_called_once()
        handle_arg = mock_worker.poll.call_args[0][0]
        assert handle_arg.id == "existing-session-123"

        # Verify success
        assert result.success
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_run_without_session_id_creates_new_session(self, supervisor: Supervisor, mock_worker: AsyncMock) -> None:
        """Test that normal flow creates a new session when no session_id provided."""
        # Mock dispatch
        mock_worker.dispatch.return_value = WorkResult(
            handle=WorkHandle(id="new-session-456"),
            prompt_sent="prompt"
        )

        # Mock successful poll
        poll_result = PollResult(
            handle=WorkHandle(id="new-session-456"),
            status="completed",
            duration_seconds=1.0,
            error=None
        )
        mock_worker.poll.return_value = poll_result

        # Mock successful sync
        sync_result = SyncResult(
            patch_result=PatchResult.applied(files_changed=["test.py"], diff_hash="abc123"),
            branch_name="test-branch"
        )
        mock_worker.sync.return_value = sync_result

        result = await supervisor.run("Test task")

        # Verify dispatcher WAS called
        mock_worker.dispatch.assert_called_once()
        # args = mock_worker.dispatch.call_args
        # assert args[1]["handle"] is None # handle kwarg should be None
        # Checking call args is tricky with AsyncMock sometimes
        _, kwargs = mock_worker.dispatch.call_args
        assert kwargs.get('handle') is None

        # Verify success
        assert result.success
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_resume_then_iterate_sends_feedback_to_same_session(
        self, supervisor: Supervisor, mock_worker: AsyncMock
    ) -> None:
        """Test that subsequent iterations send feedback to the same session instead of creating new ones."""
        # Mock poll results
        poll_result = PollResult(
            handle=WorkHandle(id="existing-session-123"),
            status="completed",
            duration_seconds=1.0,
            error=None
        )
        mock_worker.poll.return_value = poll_result # Same result for both calls is fine

        # Mock sync results
        patch_result1 = PatchResult.applied(files_changed=["test.py"], diff_hash="abc123")
        patch_result2 = PatchResult.applied(files_changed=["test.py"], diff_hash="def456")

        mock_worker.sync.side_effect = [
            SyncResult(patch_result=patch_result1, branch_name="b1"),
            SyncResult(patch_result=patch_result2, branch_name="b2")
        ]

        # Mock verifier results (fail first, pass second)
        supervisor.verifier.run_all.side_effect = [
            VerificationResult(passed=False, gates=[], duration_seconds=1.0),
            VerificationResult(passed=True, gates=[], duration_seconds=1.0)
        ]

        # Mock dispatch for 2nd iteration
        mock_worker.dispatch.return_value = WorkResult(
            handle=WorkHandle(id="existing-session-123"),
            prompt_sent="feedback"
        )

        result = await supervisor.run("Test task", session_id="existing-session-123")

        # Verify dispatch called once (for 2nd iteration)
        mock_worker.dispatch.assert_called_once()
        _, kwargs = mock_worker.dispatch.call_args
        assert kwargs['handle'].id == "existing-session-123"

        # Verify success after 2 iterations
        assert result.success
        assert result.iterations == 2

    @pytest.mark.asyncio
    async def test_resume_with_invalid_session_fails_gracefully(
        self, supervisor: Supervisor, mock_worker: AsyncMock
    ) -> None:
        """Test that invalid session ID fails gracefully with clear message."""
        # Mock API error
        mock_worker.poll.side_effect = APIError("404", status_code=404)

        result = await supervisor.run("Test task", session_id="invalid-session-999")

        # Verify failure with clear message
        assert not result.success
        assert result.failure_reason == "Invalid session ID"
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_resume_with_timeout_fails_gracefully(self, supervisor: Supervisor, mock_worker: AsyncMock) -> None:
        """Test that timeout during resume fails gracefully."""
        mock_worker.poll.side_effect = TimeoutError()

        result = await supervisor.run("Test task", session_id="slow-session-123")

        # Verify failure
        assert not result.success
        assert result.failure_reason == "Session timed out"
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_resume_patch_failure_aborts_immediately(self, supervisor: Supervisor, mock_worker: AsyncMock) -> None:
        """Test that patch failure on resumed session aborts instead of retrying."""
        # Mock poll result
        poll_result = PollResult(
            handle=WorkHandle(id="existing-session-123"),
            status="completed",
            duration_seconds=1.0,
            error=None
        )
        mock_worker.poll.return_value = poll_result

        # Mock failed patch application
        patch_result = PatchResult.failed(error="patch failed")
        mock_worker.sync.return_value = SyncResult(patch_result=patch_result, branch_name="b1")

        result = await supervisor.run("Test task", session_id="existing-session-123")

        # Verify that dispatcher was NOT called
        mock_worker.dispatch.assert_not_called()

        # Verify failure with appropriate message
        assert not result.success
        assert result.failure_reason == "Resumed session patch failed to apply"
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_run_passes_tasks_file(self, supervisor: Supervisor, mock_worker: AsyncMock) -> None:
        """Test that tasks_file is passed to prepare."""
        tasks_file = Path("tasks.md")

        # Mock poll result
        poll_result = PollResult(
            handle=WorkHandle(id="session-123"),
            status="completed",
            duration_seconds=1.0,
            error=None
        )
        mock_worker.poll.return_value = poll_result

        # Mock sync
        sync_result = SyncResult(
            patch_result=PatchResult.applied(files_changed=["test.py"], diff_hash="abc123"),
            branch_name="test-branch"
        )
        mock_worker.sync.return_value = sync_result

        # Mock dispatch
        mock_worker.dispatch.return_value = WorkResult(
            handle=WorkHandle(id="session-123"),
            prompt_sent="prompt"
        )

        await supervisor.run("Test task", tasks_file=tasks_file)

        # Verify prepare was called with tasks_file
        mock_worker.prepare.assert_called_once()
        _, kwargs = mock_worker.prepare.call_args
        assert kwargs["tasks_file"] == tasks_file
