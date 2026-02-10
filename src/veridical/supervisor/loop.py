import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from types import FrameType
from typing import TYPE_CHECKING

from rich.console import Console

from veridical.api.exceptions import APIError
from veridical.cli.progress import ProgressReporter
from veridical.models.result import LoopResult, PatchStatus
from veridical.supervisor.circuit_breaker import CircuitBreaker
from veridical.supervisor.state import LoopState, SupervisorState
from veridical.verifier.quality_gate import Verifier
from veridical.worker import WorkHandle, Worker
from veridical.worklog import WorkLogEntry, WorkLogWriter

if TYPE_CHECKING:
    from veridical.config.schema import VeridicalConfig

logger = logging.getLogger(__name__)


class Supervisor:
    """Main supervisor control loop for orchestrating worker sessions.

    The Supervisor manages the iteration cycle:
    1. Dispatch a task to Worker
    2. Poll for completion
    3. Sync the results locally
    4. Verify quality gates
    5. Loop or complete
    """

    def __init__(
        self,
        config: "VeridicalConfig",
        worker: Worker,
        repo_path: Path,
        *,
        verbose: bool = False,
        console: Console | None = None,
    ) -> None:
        """Initialize the supervisor.

        Args:
            config: Veridical configuration
            worker: Worker instance
            repo_path: Path to the repository root
            verbose: Enable verbose output
            console: Rich console instance
        """
        self.config = config
        self.worker = worker
        self.repo_path = repo_path
        self.verbose = verbose
        self.console = console or Console()
        self._current_loop_state: LoopState | None = None
        self._current_work_log_entry: WorkLogEntry | None = None
        self._iteration_start_time: datetime | None = None

        self._state = SupervisorState.IDLE
        self._circuit_breaker = CircuitBreaker(
            max_iterations=config.supervisor.max_iterations,
            max_consecutive_failures=config.supervisor.max_consecutive_failures,
            stagnation_threshold=config.supervisor.stagnation_threshold,
        )

        # Initialize components
        self.progress = ProgressReporter(console=self.console, verbose=self.verbose)
        self.verifier = Verifier(config, repo_path)

        # Configure worker with progress reporter if it supports it
        if hasattr(self.worker, "set_progress_reporter"):
            # We use type ignore because Protocol doesn't guarantee this method
            self.worker.set_progress_reporter(self.progress)  # type: ignore

        # Initialize work log writer if enabled
        self.worklog_writer: WorkLogWriter | None = None
        if config.worklog.enabled:
            self.worklog_writer = WorkLogWriter(
                project_path=repo_path,
                log_dir=config.worklog.directory,
            )

    @property
    def state(self) -> SupervisorState:
        """Get current supervisor state."""
        return self._state

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Get the circuit breaker instance."""
        return self._circuit_breaker

    def _transition_to(self, new_state: SupervisorState) -> None:
        """Transition to a new state.

        Args:
            new_state: Target state
        """
        logger.info(f"Transitioning: {self._state} -> {new_state}")
        self._state = new_state

    async def run(
        self,
        task_description: str,
        session_id: str | None = None,
        tasks_file: Path | None = None,
        target_branch: str | None = None,
        resume_from_state: bool = False,
    ) -> LoopResult:
        """Run the supervisor loop for a task.

        This is the main entry point for executing an autonomous
        quality assurance loop.

        Args:
            task_description: Description of the task to perform
            session_id: Optional session ID to resume instead of creating new session
            tasks_file: Optional path to the tasks.md file for dynamic verification
            target_branch: Optional override for the target branch

        Returns:
            Result of the loop execution
        """
        # Update verifier with the tasks file if provided
        if tasks_file:
            self.verifier.current_tasks_file = tasks_file

        state_file = self.repo_path / ".veridical_state.json"
        current_session_id: str | None = session_id
        current_handle: WorkHandle | None = WorkHandle(id=session_id) if session_id else None

        error_context: str | None = None
        started_at = datetime.now()
        start_iteration = 1
        work_branch: str | None = target_branch

        # Setup signal handlers for graceful shutdown
        def signal_handler(signum: int, _frame: FrameType | None) -> None:
            self._handle_shutdown(signum, state_file)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logger.info("Signal handlers installed (SIGINT, SIGTERM)")

        # Resume from state if requested and file exists
        if resume_from_state and state_file.exists():
            try:
                state = LoopState.load(state_file)
                logger.info(f"Resuming from saved state (Session: {state.session_id})")

                # Restore context
                current_session_id = state.session_id
                current_handle = WorkHandle(id=current_session_id)
                start_iteration = state.iteration
                error_context = state.error_context
                started_at = datetime.fromtimestamp(state.started_at_timestamp)

                # If target_branch wasn't explicitly provided, use the one from state
                if not target_branch:
                    target_branch = state.work_branch
                    work_branch = state.work_branch

                # Restore circuit breaker state roughly (iteration count)
                # We can't fully restore diff hashes but iteration count is key
                self._circuit_breaker._iteration_count = start_iteration - 1

            except Exception as e:
                logger.error(f"Failed to load state file: {e}")
                self.console.print(f"[bold red]Warning:[/bold red] Failed to load state: {e}")
                # Fallback to fresh start? Or exit?
                # For safety, let's continue as fresh if load fails, but warn.

        # Prepare worker environment
        # This should handle branch setup
        work_branch = await self.worker.prepare(
            task_description,
            target_branch,
            tasks_file=tasks_file
        )

        # Clear circuit breaker hashes if fresh start, but keep iteration if resumed
        if not resume_from_state:
            self._circuit_breaker.reset()

        try:
            with self.progress:
                while not self._circuit_breaker.is_open:
                    self._circuit_breaker.record_iteration()
                    if self._circuit_breaker.is_open:
                        break

                    iteration = self._circuit_breaker.iteration_count

                    # Update current state object for persistence
                    # We do this at start of iteration so we have a safe "checkpoint"
                    if current_session_id:
                        self._update_state(
                            task_description=task_description,
                            iteration=iteration,
                            session_id=current_session_id,
                            work_branch=work_branch or "unknown",
                            error_context=error_context,
                            started_at=started_at,
                        )
                        # Auto-save at start of iteration
                        if self._current_loop_state:
                            self._current_loop_state.save(state_file)

                    logger.info(f"--- Starting Iteration {iteration} ---")
                    self.progress.set_iterations(iteration, self.config.supervisor.max_iterations)

                    # Start work log entry for this iteration
                    self._iteration_start_time = datetime.now()
                    if self.worklog_writer and current_session_id:
                        self._current_work_log_entry = WorkLogEntry(
                            timestamp=self._iteration_start_time,
                            iteration=iteration,
                            session_id=current_session_id,
                            task_description=task_description,
                            error_context=error_context,
                        )

                    # 1. DISPATCHING or SENDING FEEDBACK
                    # Use current_session_id check to match old logic
                    if current_session_id and iteration == 1 and (session_id or resume_from_state):
                        # Resume existing session - skip dispatching
                        self.progress.set_state("Resuming session...")
                        logger.info(f"Resuming existing session: {current_session_id}")
                    else:
                        self._transition_to(SupervisorState.DISPATCHING)
                        if current_session_id and iteration > 1:
                            self.progress.set_state("Sending feedback...")
                        else:
                            self.progress.set_state("Creating session...")

                        # Ensure handle has correct iteration context
                        if current_handle:
                            current_handle.context["iteration"] = iteration

                        work_result = await self.worker.dispatch(task_description, error_context, handle=current_handle)
                        current_handle = work_result.handle
                        current_session_id = current_handle.id

                        # Log prompt if available
                        if self._current_work_log_entry and work_result.prompt_sent:
                            self._current_work_log_entry.prompt_sent = work_result.prompt_sent

                        # Update session ID in work log
                        if self._current_work_log_entry:
                            self._current_work_log_entry.session_id = current_session_id

                        # Save state immediately after dispatching (creating session/sending msg)
                        self._update_state(
                            task_description=task_description,
                            iteration=iteration,
                            session_id=current_session_id,
                            work_branch=work_branch or "unknown",
                            error_context=error_context,
                            started_at=started_at,
                        )
                        if self._current_loop_state:
                            self._current_loop_state.save(state_file)

                    # 2. POLLING
                    self._transition_to(SupervisorState.POLLING)
                    self.progress.set_state("Polling for updates...")
                    try:
                        assert current_handle is not None
                        poll_result = await self.worker.poll(current_handle)
                    except TimeoutError:
                        await self.worker.cleanup()
                        self._transition_to(SupervisorState.FAILED)
                        return LoopResult.failure_result(
                            iterations=iteration,
                            started_at=started_at,
                            failure_reason="Session timed out",
                        )
                    except Exception as e: # Catch broader exceptions from worker
                        # Handle API errors
                        await self.worker.cleanup()
                        self._transition_to(SupervisorState.FAILED)

                        if isinstance(e, APIError) and session_id and iteration == 1:
                            return LoopResult.failure_result(
                                iterations=iteration,
                                started_at=started_at,
                                failure_reason="Invalid session ID",
                                error_context=(
                                    f"The session ID '{session_id}' could not be found. "
                                    "Please verify the session ID is correct and try again.\n\n"
                                    f"Error: {e}"
                            ),
                        )

                        return LoopResult.failure_result(
                            iterations=iteration,
                            started_at=started_at,
                            failure_reason="Error during polling",
                            error_context=str(e),
                        )

                    if poll_result.status == "failed":
                        self._circuit_breaker.record_failure()
                        error_context = f"Worker session failed: {poll_result.error}"
                        continue

                    # 3. SYNCING
                    self._transition_to(SupervisorState.SYNCING)
                    self.progress.set_state("Applying patch...")

                    # Ensure handle has correct iteration context for sync
                    if current_handle:
                        current_handle.context["iteration"] = iteration

                    sync_result = await self.worker.sync(current_handle)
                    patch_result = sync_result.patch_result
                    iter_branch = sync_result.branch_name

                    # Handle rejected changes (from interactive review)
                    if patch_result.status == PatchStatus.REJECTED:
                        self._circuit_breaker.record_failure()
                        await self.worker.cleanup(iter_branch)
                        self._transition_to(SupervisorState.FAILED)
                        return LoopResult.failure_result(
                            iterations=iteration,
                            started_at=started_at,
                            failure_reason="Human review rejected",
                            error_context=patch_result.error or "Changes rejected by user",
                        )

                    if not patch_result.success:
                        self._circuit_breaker.record_failure()
                        # Clean up branch
                        if iter_branch:
                            await self.worker.cleanup(iter_branch)

                        # If this was a resumed session, abort instead of retrying
                        if session_id and iteration == 1:
                            await self.worker.cleanup()
                            self._transition_to(SupervisorState.FAILED)
                            return LoopResult.failure_result(
                                iterations=iteration,
                                started_at=started_at,
                                failure_reason="Resumed session patch failed to apply",
                                error_context=(
                                    f"The patch from session {session_id} could not be applied. "
                                    "This usually means your local code has diverged from what "
                                    "Jules worked against. Try syncing with the remote branch or "
                                    "starting a new session without --session-id.\n\n"
                                    f"Details: {patch_result.error}"
                                ),
                            )

                        # Patch failures are not recoverable - stop immediately
                        await self.worker.cleanup()
                        self._transition_to(SupervisorState.FAILED)
                        return LoopResult.failure_result(
                            iterations=iteration,
                            started_at=started_at,
                            failure_reason="Patch failed to apply",
                            error_context=(
                                f"The patch from session {current_session_id} could not be applied. "
                                "Patch failures are not recoverable through further iterations.\n\n"
                                f"Details: {patch_result.error}"
                            ),
                        )

                    # diff_hash is always set when patch is successfully applied
                    if patch_result.diff_hash:
                        self._circuit_breaker.record_diff_hash(patch_result.diff_hash)

                    # Record patch summary in work log
                    if self._current_work_log_entry and patch_result.patch_summary:
                        self._current_work_log_entry.patch_summary = patch_result.patch_summary

                    # 4. VERIFYING
                    self._transition_to(SupervisorState.VERIFYING)
                    self.progress.set_state("Running quality gates...")
                    verification_result = await self.verifier.run_all()

                    if verification_result.passed:
                        # 5. SUCCESS
                        self._transition_to(SupervisorState.SUCCESS)
                        self.progress.set_state("Merging changes...")
                        commit_hash = await self.worker.finalize(True, task_description, iter_branch)
                        self._circuit_breaker.record_success()

                        # Log successful iteration
                        self._log_iteration_end(
                            session_status="completed",
                            verification_passed=True,
                        )

                        # Cleanup state file on success
                        if state_file.exists():
                            state_file.unlink()

                        return LoopResult.success_result(
                            iterations=iteration,
                            started_at=started_at,
                            final_commit=commit_hash or "",
                            target_branch=work_branch,
                        )

                    # 6. FAILURE (Loop)
                    self._circuit_breaker.record_failure()
                    self.progress.set_state("Compiling feedback...")
                    error_context = await self.verifier.generate_feedback(verification_result)

                    # Log failed iteration
                    self._log_iteration_end(
                        session_status="completed",
                        verification_passed=False,
                        verification_errors=error_context,
                    )

                    # Cleanup failed branch
                    if iter_branch:
                        await self.worker.cleanup(iter_branch)

            # Loop terminated
            await self.worker.cleanup()
        finally:
            await self.worker.cleanup()
        self._transition_to(SupervisorState.FAILED)
        return LoopResult.failure_result(
            iterations=self._circuit_breaker.iteration_count,
            started_at=started_at,
            failure_reason=self._circuit_breaker.open_reason or "Max iterations reached",
        )

    def _update_state(
        self,
        task_description: str,
        iteration: int,
        session_id: str,
        work_branch: str,
        error_context: str | None,
        started_at: datetime,
    ) -> None:
        """Update the current state object."""
        self._current_loop_state = LoopState(
            task_description=task_description,
            iteration=iteration,
            session_id=session_id,
            work_branch=work_branch,
            error_context=error_context,
            started_at_timestamp=started_at.timestamp(),
        )

    def _log_iteration_end(
        self,
        session_status: str,
        verification_passed: bool | None = None,
        verification_errors: str | None = None,
    ) -> None:
        """Log the end of an iteration to the work log.

        Args:
            session_status: Status of the Jules session
            verification_passed: Whether verification passed
            verification_errors: Error summary if verification failed
        """
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

    def _handle_shutdown(self, signum: int, state_file: Path) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}. Saving state...")

        # Log interrupted iteration
        if self._current_work_log_entry:
            self._log_iteration_end(session_status="interrupted")

        if self._current_loop_state:
            try:
                self._current_loop_state.save(state_file)
                logger.info(f"State saved to {state_file}")
                if self.console:
                    self.console.print(
                        f"\n[yellow]Interrupted. State saved to {state_file}[/yellow]"
                    )
                    self.console.print("[dim]Run 'veridical resume' to continue later.[/dim]")
            except Exception as e:
                logger.error(f"Failed to save state: {e}")

        # Attempt to return to starting branch to leave repo clean
        # Note: Worker cleanup handles checking out starting branch if safe
        try:
             if hasattr(self.worker, "cleanup_sync"):
                 self.worker.cleanup_sync()  # type: ignore
        except Exception as e:
            logger.warning(f"Failed to cleanup branch on shutdown: {e}")

        sys.exit(0)
