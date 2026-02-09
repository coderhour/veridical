import logging
import sys
from datetime import datetime
from enum import Enum, auto
from pathlib import Path

from rich.console import Console

from veridical.cli.progress import ProgressReporter
from veridical.config.schema import VeridicalConfig
from veridical.local.runner import LocalRunner
from veridical.models.result import LoopResult
from veridical.supervisor.circuit_breaker import CircuitBreaker
from veridical.verifier.quality_gate import Verifier
from veridical.worklog import WorkLogEntry, WorkLogWriter

logger = logging.getLogger(__name__)


class LocalSupervisorState(Enum):
    """States of the local supervisor loop."""

    IDLE = auto()
    RUNNING_WORKER = auto()
    VERIFYING = auto()
    SUCCESS = auto()
    FAILED = auto()


class LocalSupervisor:
    """Orchestrates the local verify-and-fix loop."""

    def __init__(
        self,
        config: VeridicalConfig,
        repo_path: Path,
        *,
        verbose: bool = False,
        console: Console | None = None,
    ) -> None:
        """Initialize the local supervisor.

        Args:
            config: Veridical configuration
            repo_path: Path to the repository root
            verbose: Enable verbose output
            console: Rich console instance
        """
        self.config = config
        self.repo_path = repo_path
        self.verbose = verbose
        self.console = console or Console()
        self._state = LocalSupervisorState.IDLE

        # Initialize components
        self.runner = LocalRunner(config.local, console=self.console)
        self.verifier = Verifier(config, repo_path)
        self.progress = ProgressReporter(console=self.console, verbose=self.verbose)

        # Reuse existing CircuitBreaker
        self._circuit_breaker = CircuitBreaker(
            max_iterations=config.supervisor.max_iterations,
            max_consecutive_failures=config.supervisor.max_consecutive_failures,
            stagnation_threshold=config.supervisor.stagnation_threshold,
        )

        # Initialize work log writer if enabled
        self.worklog_writer: WorkLogWriter | None = None
        if config.worklog.enabled:
            self.worklog_writer = WorkLogWriter(
                project_path=repo_path,
                log_dir=config.worklog.directory,
            )
        self._current_work_log_entry: WorkLogEntry | None = None
        self._iteration_start_time: datetime | None = None

    async def run(self, task: str | None = None) -> LoopResult:
        """Run the local verification loop.

        Args:
            task: Optional task description (for logging/display)

        Returns:
            Result of the loop execution.
        """
        started_at = datetime.now()
        error_context: str | None = None

        # Reset circuit breaker
        self._circuit_breaker.reset()

        logger.info(f"Starting local supervisor loop. Task: {task}")
        if task:
            self.console.print(f"[bold blue]Task:[/bold blue] {task}")

        with self.progress:
            while not self._circuit_breaker.is_open:
                self._circuit_breaker.record_iteration()
                if self._circuit_breaker.is_open:
                    break

                iteration = self._circuit_breaker.iteration_count
                self.progress.set_iterations(iteration, self.config.supervisor.max_iterations)
                logger.info(f"--- Starting Iteration {iteration} ---")

                # Start work log entry
                self._iteration_start_time = datetime.now()
                if self.worklog_writer:
                    self._current_work_log_entry = WorkLogEntry(
                        timestamp=self._iteration_start_time,
                        iteration=iteration,
                        session_id="local-session",
                        task_description=task or "Local task",
                        error_context=error_context,
                    )

                # 1. Run Worker
                self._state = LocalSupervisorState.RUNNING_WORKER
                self.progress.set_state("Running worker command...")

                exit_code = await self.runner.run(error_context)

                if exit_code != 0:
                    logger.warning(f"Worker command failed with exit code {exit_code}")
                    # Proceed to verification to get feedback

                # 2. Verify
                self._state = LocalSupervisorState.VERIFYING
                self.progress.set_state("Running quality gates...")

                verification_result = await self.verifier.run_all()

                if verification_result.passed:
                    self._state = LocalSupervisorState.SUCCESS
                    self._circuit_breaker.record_success()
                    logger.info("Verification passed!")

                    self._log_iteration_end(
                        session_status="completed",
                        verification_passed=True,
                    )

                    return LoopResult.success_result(
                        iterations=iteration,
                        started_at=started_at,
                        final_commit=None,
                        target_branch="local",  # No branch management in local mode
                    )

                # 3. Handle Failure
                self._circuit_breaker.record_failure()
                self.progress.set_state("Compiling feedback...")
                error_context = await self.verifier.generate_feedback(verification_result)

                logger.info(f"Verification failed. Feedback generated ({len(error_context)} chars).")

                self._log_iteration_end(
                    session_status="completed",
                    verification_passed=False,
                    verification_errors=error_context,
                )

        # Loop terminated
        self._state = LocalSupervisorState.FAILED
        failure_reason = self._circuit_breaker.open_reason or "Max iterations reached"
        logger.warning(f"Loop failed: {failure_reason}")

        return LoopResult.failure_result(
            iterations=self._circuit_breaker.iteration_count,
            started_at=started_at,
            failure_reason=failure_reason,
            error_context=error_context,
        )

    def _log_iteration_end(
        self,
        session_status: str,
        verification_passed: bool | None = None,
        verification_errors: str | None = None,
    ) -> None:
        """Log the end of an iteration to the work log."""
        if not self.worklog_writer or not self._current_work_log_entry:
            return

        # Calculate duration
        duration = None
        if self._iteration_start_time:
            duration = (datetime.now() - self._iteration_start_time).total_seconds()

        # Update entry with results
        self._current_work_log_entry.session_status = session_status
        self._current_work_log_entry.verification_passed = verification_passed
        self._current_work_log_entry.verification_errors = verification_errors
        self._current_work_log_entry.duration_seconds = duration

        # Write to log
        try:
            self.worklog_writer.write(self._current_work_log_entry)
            logger.debug(
                f"Work log entry written for iteration {self._current_work_log_entry.iteration}"
            )
        except Exception as e:
            logger.warning(f"Failed to write work log entry: {e}")
