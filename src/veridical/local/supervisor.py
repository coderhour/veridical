import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from types import FrameType
from typing import TYPE_CHECKING

from rich.console import Console

from veridical.cli.progress import ProgressReporter
from veridical.local.runner import LocalRunner
from veridical.models.result import LoopResult
from veridical.supervisor.circuit_breaker import CircuitBreaker
from veridical.verifier.quality_gate import Verifier
from veridical.worklog import WorkLogEntry, WorkLogWriter

if TYPE_CHECKING:
    from veridical.config.schema import VeridicalConfig

logger = logging.getLogger(__name__)


class LocalSupervisor:
    """Orchestrates the local verify-and-fix loop."""

    def __init__(
        self,
        config: "VeridicalConfig",
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

        self._circuit_breaker = CircuitBreaker(
            max_iterations=config.supervisor.max_iterations,
            max_consecutive_failures=config.supervisor.max_consecutive_failures,
            stagnation_threshold=config.supervisor.stagnation_threshold,
        )

        self.runner = LocalRunner(config.local)
        self.verifier = Verifier(config, repo_path)
        self.progress = ProgressReporter(console=self.console, verbose=self.verbose)

        # Work log writer
        self.worklog_writer: WorkLogWriter | None = None
        if config.worklog.enabled:
            self.worklog_writer = WorkLogWriter(
                project_path=repo_path,
                log_dir=config.worklog.directory,
            )

    async def run(
        self,
        task: str,
        tasks_file: Path | None = None,
    ) -> LoopResult:
        """Run the local loop."""
        if tasks_file:
            self.verifier.current_tasks_file = tasks_file

        started_at = datetime.now()
        error_context: str | None = None

        # Setup signal handlers
        def signal_handler(signum: int, _frame: FrameType | None) -> None:
            logger.info(f"Received signal {signum}. Exiting...")
            sys.exit(0)

        # Only set signal handlers if running in main thread
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except ValueError:
            # Not in main thread, skip signal handlers
            pass

        with self.progress:
            while not self._circuit_breaker.is_open:
                self._circuit_breaker.record_iteration()
                if self._circuit_breaker.is_open:
                    break

                iteration = self._circuit_breaker.iteration_count
                logger.info(f"--- Starting Local Iteration {iteration} ---")
                self.progress.set_iterations(iteration, self.config.supervisor.max_iterations)

                iteration_start_time = datetime.now()

                # Create work log entry
                current_entry = None
                if self.worklog_writer:
                    current_entry = WorkLogEntry(
                        timestamp=iteration_start_time,
                        iteration=iteration,
                        session_id="local-loop",
                        task_description=task,
                        error_context=error_context,
                    )

                # 1. RUN WORKER
                self.progress.set_state("Running worker...")
                worker_exit_code = await self.runner.run(task, error_context)

                if worker_exit_code != 0:
                    # Not necessarily a failure of the loop, but the worker might have crashed
                    # or just failed to produce output.
                    # We continue to verification to see if anything changed or is broken.
                    logger.warning(f"Worker exited with code {worker_exit_code}")

                # 2. VERIFY
                self.progress.set_state("Verifying...")
                verification_result = await self.verifier.run_all()

                # Check verification result
                if verification_result.passed:
                    self._circuit_breaker.record_success()
                    logger.info("Verification passed!")

                    if current_entry and self.worklog_writer:
                        current_entry.verification_passed = True
                        current_entry.session_status = "completed"
                        current_entry.duration_seconds = (
                            datetime.now() - iteration_start_time
                        ).total_seconds()
                        self.worklog_writer.write(current_entry)

                    return LoopResult.success_result(
                        iterations=iteration,
                        started_at=started_at,
                        final_commit="local-changes",  # No commit in local mode usually
                        target_branch="current",
                    )

                # 3. FEEDBACK
                self._circuit_breaker.record_failure()
                self.progress.set_state("Generating feedback...")
                error_context = await self.verifier.generate_feedback(verification_result)

                if current_entry and self.worklog_writer:
                    current_entry.verification_passed = False
                    current_entry.verification_errors = error_context
                    current_entry.session_status = "completed"
                    current_entry.duration_seconds = (
                        datetime.now() - iteration_start_time
                    ).total_seconds()
                    self.worklog_writer.write(current_entry)

        return LoopResult.failure_result(
            iterations=self._circuit_breaker.iteration_count,
            started_at=started_at,
            failure_reason=self._circuit_breaker.open_reason or "Max iterations reached",
        )
