"""Tests for supervisor session resume functionality."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

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
            state=SessionState.RUNNING,
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
    async def test_resume_then_iterate_creates_new_session(self, supervisor: Supervisor) -> None:
        """Test that subsequent iterations create new sessions after resume."""
        # Mock session creation for iteration 2
        mock_session = SessionResponse(
            name="sessions/new-session-789",
            state=SessionState.RUNNING,
        )

        # Mock poll results
        now = datetime.now()
        poll_result_iter1 = PollResult(
            session_id="existing-session-123",
            final_state=SessionState.COMPLETED,
            started_at=now,
            completed_at=now,
            poll_count=1,
        )
        poll_result_iter2 = PollResult(
            session_id="new-session-789",
            final_state=SessionState.COMPLETED,
            started_at=now,
            completed_at=now,
            poll_count=1,
        )

        # Mock patch results
        patch_result = PatchResult.applied(files_changed=["test.py"], diff_hash="abc123")

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

        with (
            patch.object(
                supervisor.dispatcher, "create_session", return_value=mock_session
            ) as mock_create_session,
            patch.object(
                supervisor.poller,
                "wait_for_completion",
                side_effect=[poll_result_iter1, poll_result_iter2],
            ),
            patch.object(
                supervisor.synchronizer, "create_iteration_branch", return_value="test-branch"
            ),
            patch.object(supervisor.synchronizer, "apply_session_patch", return_value=patch_result),
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

            # Verify dispatcher was called once (for iteration 2, not iteration 1)
            assert mock_create_session.call_count == 1

            # Verify success after 2 iterations
            assert result.success
            assert result.iterations == 2

    @pytest.mark.asyncio
    async def test_resume_with_invalid_session_fails_gracefully(
        self, supervisor: Supervisor
    ) -> None:
        """Test that invalid session ID fails gracefully through poller."""
        # Mock timeout error from poller
        with patch.object(supervisor.poller, "wait_for_completion", side_effect=TimeoutError()):
            result = await supervisor.run("Test task", session_id="invalid-session-999")

            # Verify failure
            assert not result.success
            assert result.failure_reason == "Session timed out"
            assert result.iterations == 1
