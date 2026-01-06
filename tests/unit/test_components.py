"""Tests for component interfaces."""

from pathlib import Path

import pytest

from veridical.config.schema import VerifierConfig
from veridical.dispatcher.agents_md import AgentsMdInjector
from veridical.dispatcher.prompt import PromptBuilder
from veridical.models.result import GateResult, GateStatus, VerificationResult
from veridical.poller.backoff import ConstantBackoff, ExponentialBackoff
from veridical.supervisor.circuit_breaker import CircuitBreaker
from veridical.supervisor.state import SupervisorState, is_valid_transition
from veridical.verifier.feedback import FeedbackGenerator


@pytest.mark.unit
class TestSupervisorState:
    """Tests for SupervisorState enum."""

    def test_terminal_states(self) -> None:
        """Test terminal state detection."""
        assert SupervisorState.SUCCESS.is_terminal()
        assert SupervisorState.FAILED.is_terminal()
        assert not SupervisorState.IDLE.is_terminal()

    def test_active_states(self) -> None:
        """Test active state detection."""
        assert SupervisorState.DISPATCHING.is_active()
        assert SupervisorState.POLLING.is_active()
        assert not SupervisorState.IDLE.is_active()
        assert not SupervisorState.SUCCESS.is_active()

    def test_valid_transitions(self) -> None:
        """Test state transition validation."""
        assert is_valid_transition(SupervisorState.IDLE, SupervisorState.DISPATCHING)
        assert is_valid_transition(SupervisorState.DISPATCHING, SupervisorState.POLLING)
        assert not is_valid_transition(SupervisorState.IDLE, SupervisorState.VERIFYING)
        assert not is_valid_transition(SupervisorState.SUCCESS, SupervisorState.IDLE)


@pytest.mark.unit
class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initial_state(self) -> None:
        """Test initial circuit state."""
        cb = CircuitBreaker()
        assert not cb.is_open
        assert cb.iteration_count == 0

    def test_max_iterations(self) -> None:
        """Test circuit opens after max iterations."""
        cb = CircuitBreaker(max_iterations=3)
        for _ in range(4):
            cb.record_iteration()
        assert cb.is_open
        assert "iterations" in cb.open_reason.lower()

    def test_consecutive_failures(self) -> None:
        """Test circuit opens after consecutive failures."""
        cb = CircuitBreaker(max_consecutive_failures=2)
        cb.record_failure()
        assert not cb.is_open
        cb.record_failure()
        assert cb.is_open
        assert "failures" in cb.open_reason.lower()

    def test_success_resets_failures(self) -> None:
        """Test success resets failure count."""
        cb = CircuitBreaker(max_consecutive_failures=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open

    def test_stagnation_detection(self) -> None:
        """Test stagnation detection via diff hashes."""
        cb = CircuitBreaker(stagnation_threshold=3)
        cb.record_diff_hash("abc123")
        cb.record_diff_hash("abc123")
        assert not cb.is_open
        cb.record_diff_hash("abc123")
        assert cb.is_open
        assert "stagnation" in cb.open_reason.lower()

    def test_reset(self) -> None:
        """Test circuit reset."""
        cb = CircuitBreaker(max_iterations=2)
        cb.record_iteration()
        cb.record_iteration()
        cb.record_iteration()
        assert cb.is_open
        cb.reset()
        assert not cb.is_open
        assert cb.iteration_count == 0


@pytest.mark.unit
class TestPromptBuilder:
    """Tests for PromptBuilder."""

    def test_basic_prompt(self) -> None:
        """Test basic prompt construction."""
        builder = PromptBuilder()
        prompt = builder.build_prompt("Fix the bug")
        assert "Fix the bug" in prompt
        assert "## Task" in prompt
        assert "## Constraints" in prompt

    def test_prompt_with_error_context(self) -> None:
        """Test prompt with error context."""
        builder = PromptBuilder()
        prompt = builder.build_prompt("Fix the bug", error_context="Test failed: AssertionError")
        assert "Test failed: AssertionError" in prompt
        assert "previous attempt failed" in prompt.lower()

    def test_prompt_with_extra_constraints(self) -> None:
        """Test prompt with extra constraints."""
        builder = PromptBuilder()
        prompt = builder.build_prompt(
            "Fix the bug",
            extra_constraints=["No any types", "Full test coverage"],
        )
        assert "No any types" in prompt
        assert "Full test coverage" in prompt


@pytest.mark.unit
class TestAgentsMdInjector:
    """Tests for AgentsMdInjector."""

    def test_inject_constraints(self, temp_dir: Path) -> None:
        """Test constraint injection."""
        # Create AGENTS.md
        agents_md = temp_dir / "AGENTS.md"
        agents_md.write_text("# Project Rules\n\n- Rule 1\n")

        injector = AgentsMdInjector(temp_dir)
        result = injector.inject_constraints(["Extra constraint 1"])

        assert "# Project Rules" in result
        assert "Extra constraint 1" in result
        assert "EPHEMERAL CONSTRAINT" in result

    def test_strip_ephemeral(self) -> None:
        """Test ephemeral section removal."""
        injector = AgentsMdInjector(Path())
        content = """\
# Rules

<!-- VERIDICAL:EPHEMERAL -->
# EPHEMERAL CONSTRAINT
- temp constraint
<!-- VERIDICAL:EPHEMERAL -->

# More rules
"""
        stripped = injector.strip_ephemeral(content)
        assert "temp constraint" not in stripped
        assert "# Rules" in stripped
        assert "# More rules" in stripped


@pytest.mark.unit
class TestBackoff:
    """Tests for backoff strategies."""

    def test_exponential_backoff(self) -> None:
        """Test exponential backoff progression."""
        backoff = ExponentialBackoff(
            base_interval=10.0,
            max_interval=100.0,
            jitter_factor=0.0,
        )
        assert backoff.get_delay(0) == 10.0
        assert backoff.get_delay(1) == 20.0
        assert backoff.get_delay(2) == 40.0
        assert backoff.get_delay(10) == 100.0  # Capped

    def test_exponential_backoff_with_jitter(self) -> None:
        """Test that jitter is applied."""
        backoff = ExponentialBackoff(
            base_interval=100.0,
            jitter_factor=0.1,
        )
        # Get multiple samples
        delays = [backoff.get_delay(0) for _ in range(10)]
        # Should have some variation
        assert len(set(delays)) > 1

    def test_constant_backoff(self) -> None:
        """Test constant backoff."""
        backoff = ConstantBackoff(interval=30.0)
        assert backoff.get_delay(0) == 30.0
        assert backoff.get_delay(5) == 30.0
        assert backoff.get_delay(100) == 30.0


@pytest.mark.unit
class TestFeedbackGenerator:
    """Tests for FeedbackGenerator."""

    @pytest.mark.asyncio
    async def test_no_feedback_on_success(self) -> None:
        """Test empty feedback when all gates pass."""
        gen = FeedbackGenerator(config=VerifierConfig())
        result = VerificationResult(passed=True, gates=[], duration_seconds=1.0)
        assert await gen.generate_feedback(result) == ""

    @pytest.mark.asyncio
    async def test_feedback_on_failure(self) -> None:
        """Test feedback generation on failure."""
        gen = FeedbackGenerator(config=VerifierConfig())
        result = VerificationResult(
            passed=False,
            gates=[
                GateResult(
                    name="pytest",
                    command="pytest",
                    status=GateStatus.FAILED,
                    exit_code=1,
                    output="FAILED test_foo.py::test_bar",
                    error_output="",
                    duration_seconds=1.0,
                )
            ],
            duration_seconds=1.0,
        )
        feedback = await gen.generate_feedback(result)
        assert "pytest" in feedback
        assert "FAILED" in feedback

    @pytest.mark.asyncio
    async def test_feedback_truncation(self) -> None:
        """Test feedback truncation."""
        config = VerifierConfig(summary_max_length=100)
        gen = FeedbackGenerator(config=config)
        result = VerificationResult(
            passed=False,
            gates=[
                GateResult(
                    name="test",
                    command="test",
                    status=GateStatus.FAILED,
                    exit_code=1,
                    output="x" * 1000,
                    error_output="",
                    duration_seconds=1.0,
                )
            ],
            duration_seconds=1.0,
        )
        feedback = await gen.generate_feedback(result)
        assert len(feedback) <= 100
        assert feedback.endswith("...")
