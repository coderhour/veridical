"""Tests for supervisor session resume functionality."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from veridical.api.exceptions import APIError
from veridical.api.models import SessionResponse, SessionState
from veridical.config.schema import (
    GitConfig,
    JulesConfig,
    SupervisorConfig,
    VeridicalConfig,
    VerifierConfig,
)
from veridical.models.result import VerificationResult
from veridical.poller.monitor import PollResult
from veridical.supervisor.loop import Supervisor
from veridical.synchronizer.patch import PatchResult


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
    def mock_client(self) -> AsyncMock:
        """Create a mock Jules client."""
        return AsyncMock()

    @pytest.fixture
    def supervisor(self, mock_config: VeridicalConfig) -> Supervisor:
        """Create a supervisor instance with mocked dependencies."""
        return Supervisor(mock_config, AsyncMock(), Path("/tmp/test"))

    @pytest.mark.asyncio
    async def test_run_with_session_id_skips_dispatching(self, supervisor: Supervisor) -> None:
        """Test that providing session_id skips dispatching on first iteration."""
        # Mock successful poll result
        poll_result = PollResult(
            session_id="existing-session-123",
            final_state=SessionState.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            poll_count=1,
        )

        # Mock successful patch application
        patch_result = PatchResult.applied(files_changed=["test.py"], diff_hash="abc123")

        # Mock successful verification
        verification_result = VerificationResult(
            passed=True,
            gates=[],
            duration_seconds=1.0,
        )

        with (
            patch.object(supervisor.poller, "wait_for_completion", return_value=poll_result),
            patch.object(
                supervisor.synchronizer, "create_iteration_branch", return_value="test-branch"
            ),
            patch.object(supervisor.synchronizer, "apply_session_patch", return_value=patch_result),
            patch.object(supervisor.verifier, "run_all", return_value=verification_result),
            patch.object(supervisor.synchronizer, "merge_to_main", return_value="commit123"),
            patch.object(supervisor.dispatcher, "create_session") as mock_create_session,
        ):
            result = await supervisor.run("Test task", session_id="existing-session-123")

            # Verify dispatcher was NOT called on first iteration
            mock_create_session.assert_not_called()

            # Verify success
            assert result.success
            assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_run_without_session_id_creates_new_session(self, supervisor: Supervisor) -> None:
        """Test that normal flow creates a new session when no session_id provided."""
        # Mock session creation
        mock_session = SessionResponse(
            name="sessions/new-session-456",
            state=SessionState.IN_PROGRESS,
        )

        # Mock successful poll result
        poll_result = PollResult(
            session_id="new-session-456",
            final_state=SessionState.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            poll_count=1,
        )

        # Mock successful patch application
        patch_result = PatchResult.applied(files_changed=["test.py"], diff_hash="abc123")

        # Mock successful verification
        verification_result = VerificationResult(
            passed=True,
            gates=[],
            duration_seconds=1.0,
        )

        with (
            patch.object(
                supervisor.dispatcher, "create_session", return_value=mock_session
            ) as mock_create_session,
            patch.object(supervisor.poller, "wait_for_completion", return_value=poll_result),
            patch.object(
                supervisor.synchronizer, "create_iteration_branch", return_value="test-branch"
            ),
            patch.object(supervisor.synchronizer, "apply_session_patch", return_value=patch_result),
            patch.object(supervisor.verifier, "run_all", return_value=verification_result),
            patch.object(supervisor.synchronizer, "merge_to_main", return_value="commit123"),
        ):
            result = await supervisor.run("Test task")

            # Verify dispatcher WAS called
            mock_create_session.assert_called_once()

            # Verify success
            assert result.success
            assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_resume_then_iterate_sends_feedback_to_same_session(
        self, supervisor: Supervisor
    ) -> None:
        """Test that subsequent iterations send feedback to the same session instead of creating new ones."""
        # Mock poll results - both iterations use the same session
        now = datetime.now()
        poll_result_iter1 = PollResult(
            session_id="existing-session-123",
            final_state=SessionState.COMPLETED,
            started_at=now,
            completed_at=now,
            poll_count=1,
        )
        poll_result_iter2 = PollResult(
            session_id="existing-session-123",  # Same session
            final_state=SessionState.COMPLETED,
            started_at=now,
            completed_at=now,
            poll_count=1,
        )

        # Mock patch results (different hashes to avoid stagnation detection)
        patch_result1 = PatchResult.applied(files_changed=["test.py"], diff_hash="abc123")
        patch_result2 = PatchResult.applied(files_changed=["test.py"], diff_hash="def456")

        # Mock verification results (fail first, pass second)
        verification_result_fail = VerificationResult(
            passed=False,
            gates=[],
            duration_seconds=1.0,
        )
        verification_result_pass = VerificationResult(
            passed=True,
            gates=[],
            duration_seconds=1.0,
        )

        # Create a mock for the client's send_message method
        mock_send_message = AsyncMock()

        with (
            patch.object(supervisor.dispatcher, "create_session") as mock_create_session,
            patch.object(supervisor.client, "send_message", mock_send_message),
            patch.object(
                supervisor.poller,
                "wait_for_completion",
                side_effect=[poll_result_iter1, poll_result_iter2],
            ),
            patch.object(
                supervisor.synchronizer, "create_iteration_branch", return_value="test-branch"
            ),
            patch.object(
                supervisor.synchronizer,
                "apply_session_patch",
                side_effect=[patch_result1, patch_result2],
            ),
            patch.object(
                supervisor.verifier,
                "run_all",
                side_effect=[verification_result_fail, verification_result_pass],
            ),
            patch.object(supervisor.verifier, "generate_feedback", return_value="Test failed"),
            patch.object(supervisor.synchronizer, "cleanup_branch"),
            patch.object(supervisor.synchronizer, "merge_to_main", return_value="commit123"),
        ):
            result = await supervisor.run("Test task", session_id="existing-session-123")

            # Verify dispatcher was NOT called (we never create a new session)
            mock_create_session.assert_not_called()

            # Verify send_message was called for iteration 2
            mock_send_message.assert_called_once()
            call_args = mock_send_message.call_args
            assert call_args[0][0] == "existing-session-123"  # Same session ID

            # Verify success after 2 iterations
            assert result.success
            assert result.iterations == 2

    @pytest.mark.asyncio
    async def test_resume_with_invalid_session_fails_gracefully(
        self, supervisor: Supervisor
    ) -> None:
        """Test that invalid session ID fails gracefully with clear message."""
        # Mock API error (404 Not Found) from poller
        api_error = APIError(
            "API request failed: 404",
            status_code=404,
            response_body='{"error": "Session not found"}',
        )
        with patch.object(supervisor.poller, "wait_for_completion", side_effect=api_error):
            result = await supervisor.run("Test task", session_id="invalid-session-999")

            # Verify failure with clear message
            assert not result.success
            assert result.failure_reason == "Invalid session ID"
            assert "invalid-session-999" in result.error_context
            assert "could not be found" in result.error_context
            assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_resume_with_timeout_fails_gracefully(self, supervisor: Supervisor) -> None:
        """Test that timeout during resume fails gracefully."""
        # Mock timeout error from poller
        with patch.object(supervisor.poller, "wait_for_completion", side_effect=TimeoutError()):
            result = await supervisor.run("Test task", session_id="slow-session-123")

            # Verify failure
            assert not result.success
            assert result.failure_reason == "Session timed out"
            assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_resume_patch_failure_aborts_immediately(self, supervisor: Supervisor) -> None:
        """Test that patch failure on resumed session aborts instead of retrying."""
        # Mock successful poll result
        poll_result = PollResult(
            session_id="existing-session-123",
            final_state=SessionState.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            poll_count=1,
        )

        # Mock failed patch application
        patch_result = PatchResult.failed(error="patch failed: README.md: patch does not apply")

        with (
            patch.object(supervisor.poller, "wait_for_completion", return_value=poll_result),
            patch.object(
                supervisor.synchronizer, "create_iteration_branch", return_value="test-branch"
            ),
            patch.object(supervisor.synchronizer, "apply_session_patch", return_value=patch_result),
            patch.object(supervisor.synchronizer, "cleanup_branch"),
            patch.object(supervisor.dispatcher, "create_session") as mock_create_session,
        ):
            result = await supervisor.run("Test task", session_id="existing-session-123")

            # Verify that dispatcher was NOT called (should abort, not retry)
            mock_create_session.assert_not_called()

            # Verify failure with appropriate message
            assert not result.success
            assert result.failure_reason == "Resumed session patch failed to apply"
            assert "existing-session-123" in result.error_context
            assert "diverged" in result.error_context
            assert result.iterations == 1
