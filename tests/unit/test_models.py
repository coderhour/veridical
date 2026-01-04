"""Tests for core data models."""

from datetime import datetime, timedelta

import pytest

from veridical.models.iteration import IterationContext
from veridical.models.result import (
    GateResult,
    GateStatus,
    LoopResult,
    PatchResult,
    PatchStatus,
    VerificationResult,
)
from veridical.models.session import SessionInfo, SessionStatus


@pytest.mark.unit
class TestSessionStatus:
    """Tests for SessionStatus enum."""

    def test_terminal_states(self) -> None:
        """Test terminal state detection."""
        assert SessionStatus.COMPLETED.is_terminal()
        assert SessionStatus.FAILED.is_terminal()
        assert not SessionStatus.QUEUED.is_terminal()
        assert not SessionStatus.IN_PROGRESS.is_terminal()

    def test_waiting_states(self) -> None:
        """Test waiting state detection."""
        assert SessionStatus.AWAITING_PLAN_APPROVAL.is_waiting()
        assert SessionStatus.AWAITING_USER_FEEDBACK.is_waiting()
        assert not SessionStatus.IN_PROGRESS.is_waiting()
        assert not SessionStatus.COMPLETED.is_waiting()


@pytest.mark.unit
class TestSessionInfo:
    """Tests for SessionInfo model."""

    def test_basic_creation(self) -> None:
        """Test basic session info creation."""
        info = SessionInfo(
            session_id="session-123",
            status=SessionStatus.IN_PROGRESS,
        )
        assert info.session_id == "session-123"
        assert info.status == SessionStatus.IN_PROGRESS

    def test_full_creation(self) -> None:
        """Test session info with all fields."""
        now = datetime.now()
        info = SessionInfo(
            session_id="session-123",
            status=SessionStatus.FAILED,
            created_at=now,
            updated_at=now,
            branch="main",
            prompt="Fix the bug",
            error_message="Something went wrong",
        )
        assert info.error_message == "Something went wrong"


@pytest.mark.unit
class TestIterationContext:
    """Tests for IterationContext model."""

    def test_basic_creation(self) -> None:
        """Test basic iteration context creation."""
        ctx = IterationContext(iteration_number=0)
        assert ctx.iteration_number == 0
        assert ctx.session_id is None

    def test_duration_calculation(self) -> None:
        """Test duration calculation."""
        start = datetime.now()
        ctx = IterationContext(
            iteration_number=1,
            started_at=start,
            completed_at=start + timedelta(seconds=60),
        )
        assert ctx.duration_seconds == 60.0

    def test_duration_none_when_incomplete(self) -> None:
        """Test duration is None when not completed."""
        ctx = IterationContext(iteration_number=0)
        assert ctx.duration_seconds is None

    def test_with_completion(self) -> None:
        """Test with_completion method."""
        ctx = IterationContext(iteration_number=0)
        completed = ctx.with_completion()
        assert completed.completed_at is not None
        assert ctx.completed_at is None  # Original unchanged

    def test_with_error_context(self) -> None:
        """Test with_error_context method."""
        ctx = IterationContext(iteration_number=0)
        with_error = ctx.with_error_context("Test failed")
        assert with_error.error_context == "Test failed"
        assert ctx.error_context is None  # Original unchanged


@pytest.mark.unit
class TestLoopResult:
    """Tests for LoopResult model."""

    def test_success_result_factory(self) -> None:
        """Test success result factory method."""
        start = datetime.now()
        result = LoopResult.success_result(
            iterations=3,
            started_at=start,
            final_commit="abc123",
        )
        assert result.success is True
        assert result.iterations == 3
        assert result.final_commit == "abc123"
        assert result.failure_reason is None

    def test_failure_result_factory(self) -> None:
        """Test failure result factory method."""
        start = datetime.now()
        result = LoopResult.failure_result(
            iterations=5,
            started_at=start,
            failure_reason="Max iterations exceeded",
            error_context="Last error was...",
        )
        assert result.success is False
        assert result.failure_reason == "Max iterations exceeded"
        assert result.error_context == "Last error was..."

    def test_duration_calculation(self) -> None:
        """Test duration calculation."""
        start = datetime.now()
        result = LoopResult(
            success=True,
            iterations=1,
            started_at=start,
            completed_at=start + timedelta(minutes=5),
        )
        assert result.duration_seconds == 300.0


@pytest.mark.unit
class TestGateResult:
    """Tests for GateResult model."""

    def test_passed_property(self) -> None:
        """Test passed property."""
        passed = GateResult(
            name="pytest",
            command="pytest",
            status=GateStatus.PASSED,
            exit_code=0,
            duration_seconds=10.0,
        )
        assert passed.passed is True

        failed = GateResult(
            name="ruff",
            command="ruff check",
            status=GateStatus.FAILED,
            exit_code=1,
            duration_seconds=5.0,
        )
        assert failed.passed is False


@pytest.mark.unit
class TestVerificationResult:
    """Tests for VerificationResult model."""

    def test_failed_gates_property(self) -> None:
        """Test failed_gates property."""
        result = VerificationResult(
            passed=False,
            duration_seconds=15.0,
            gates=[
                GateResult(
                    name="pytest",
                    command="pytest",
                    status=GateStatus.PASSED,
                    exit_code=0,
                    duration_seconds=10.0,
                ),
                GateResult(
                    name="ruff",
                    command="ruff check",
                    status=GateStatus.FAILED,
                    exit_code=1,
                    duration_seconds=5.0,
                ),
            ],
        )
        assert len(result.failed_gates) == 1
        assert result.failed_gate_names == ["ruff"]


@pytest.mark.unit
class TestPatchResult:
    """Tests for PatchResult model."""

    def test_applied_factory(self) -> None:
        """Test applied factory method."""
        result = PatchResult.applied(
            files_changed=["src/main.py", "tests/test_main.py"],
            diff_hash="abc123",
        )
        assert result.success is True
        assert result.status == PatchStatus.APPLIED
        assert len(result.files_changed) == 2

    def test_failed_factory(self) -> None:
        """Test failed factory method."""
        result = PatchResult.failed("Patch conflict", status=PatchStatus.CONFLICT)
        assert result.success is False
        assert result.status == PatchStatus.CONFLICT
        assert result.error == "Patch conflict"
