import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from types import FrameType
from typing import TYPE_CHECKING

from rich.console import Console

from veridical.diagnose import Localizer
from veridical.learning.rules import RuleManager
from veridical.models.result import LoopResult
from veridical.supervisor.circuit_breaker import CircuitBreaker
from veridical.supervisor.state import LoopState, SupervisorState
from veridical.verifier.quality_gate import Verifier
from veridical.worker.models import WorkStatus
from veridical.worklog import WorkLogEntry, WorkLogWriter

if TYPE_CHECKING:
    from veridical.config.schema import VeridicalConfig
    from veridical.synchronizer.patch import Synchronizer
    from veridical.worker.protocol import Worker

logger = logging.getLogger(__name__)


class Supervisor:
    """Main supervisor control loop for orchestrating Jules sessions.

    The Supervisor manages the iteration cycle:
    1. Dispatch a task to Jules
    2. Poll for completion
    3. Sync the results locally
    4. Verify quality gates
    5. Loop or complete
    """

    def __init__(
        self,
        config: "VeridicalConfig",
        worker: "Worker",
        repo_path: Path,
        *,
        verbose: bool = False,
        console: Console | None = None,
    ) -> None:
        """Initialize the supervisor.

        Args:
            config: Veridical configuration
            worker: Worker instance implementing the Worker protocol
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

        # Initialize verifier (the only component the supervisor owns directly)
        self.verifier = Verifier(config, repo_path)
        # Jules mode: disable autofix since Jules runs on a remote VM
        # and does not support uploading local patches
        self.verifier.autofix_enabled = False

        # Initialize localizer
        self.localizer = Localizer(repo_path)

        # Load learned rules if auto-inject is enabled
        self._learned_rules_context: str | None = None
        if config.learning.auto_inject_rules:
            self._learned_rules_context = self._load_learned_rules_context(
                repo_path / config.learning.rules_file
            )

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

    def _get_synchronizer(self) -> "Synchronizer":
        """Get the synchronizer from the worker for branch management.

        Returns:
            Synchronizer instance from the worker

        Raises:
            AttributeError: If the worker does not expose a synchronizer
        """
        sync = getattr(self.worker, "synchronizer", None)
        if sync is None:
            raise AttributeError(
                f"Worker {type(self.worker).__name__} does not expose a 'synchronizer' attribute. "
                "Branch management requires a synchronizer."
            )
        return sync

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
            resume_from_state: Whether to resume from a saved state file

        Returns:
            Result of the loop execution
        """
        # Update verifier with the tasks file if provided
        if tasks_file:
            self.verifier.current_tasks_file = tasks_file
            # Also propagate to worker's dispatcher if available
            dispatcher = getattr(self.worker, "dispatcher", None)
            if dispatcher is not None:
                dispatcher.current_tasks_file = tasks_file

        synchronizer = self._get_synchronizer()

        state_file = self.repo_path / ".veridical_state.json"
        current_session_id: str | None = session_id
        error_context: str | None = None
        started_at = datetime.now()
        start_iteration = 1

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
                start_iteration = state.iteration
                error_context = state.error_context
                started_at = datetime.fromtimestamp(state.started_at_timestamp)

                # If target_branch wasn't explicitly provided, use the one from state
                if not target_branch:
                    target_branch = state.work_branch

                # Restore circuit breaker state roughly (iteration count)
                # We can't fully restore diff hashes but iteration count is key
                self._circuit_breaker._iteration_count = start_iteration - 1

            except Exception as e:
                logger.error(f"Failed to load state file: {e}")
                self.console.print(f"[bold red]Warning:[/bold red] Failed to load state: {e}")

        # Set up work branch for this run
        synchronizer.setup_work_branch(task_description, target_branch)

        # Clear circuit breaker hashes if fresh start, but keep iteration if resumed
        if not resume_from_state:
            self._circuit_breaker.reset()

        # Use worker's progress context manager if available
        progress = getattr(self.worker, "progress", None)
        progress_ctx = progress if progress is not None else _noop_context()

        with progress_ctx:
            while not self._circuit_breaker.is_open:
                self._circuit_breaker.record_iteration()
                if self._circuit_breaker.is_open:
                    break

                iteration = self._circuit_breaker.iteration_count

                # Update current state object for persistence
                if current_session_id:
                    self._update_state(
                        task_description=task_description,
                        iteration=iteration,
                        session_id=current_session_id,
                        work_branch=synchronizer.work_branch or "unknown",
                        error_context=error_context,
                        started_at=started_at,
                    )
                    # Auto-save at start of iteration
                    if self._current_loop_state:
                        self._current_loop_state.save(state_file)

                logger.info(f"--- Starting Iteration {iteration} ---")

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

                # 1. DISPATCHING via Worker
                self._transition_to(SupervisorState.DISPATCHING)

                # PRE-LOCALIZATION ENRICHMENT
                current_task = task_description
                current_error = error_context

                # Inject learned rules into dispatch prompt
                if self._learned_rules_context and iteration == 1:
                    current_task = (
                        f"{current_task}\n\nLearned Rules:\n{self._learned_rules_context}"
                    )

                try:
                    if iteration == 1:
                        # On first iteration, try to localize based on task description
                        report = self.localizer.localize(task_description)
                        loc_info = report.to_feedback_string()
                        if loc_info:
                            logger.info(f"Enriching initial task with localization: {loc_info}")
                            current_task = (
                                f"{task_description}\n\nLocalization Analysis: {loc_info}"
                            )

                    if current_error:
                        # On retries, enrich error context with localization
                        report = self.localizer.localize(current_error)
                        loc_info = report.to_feedback_string()
                        if loc_info:
                            logger.info(
                                f"Enriching retry error context with localization: {loc_info}"
                            )
                            current_error = f"{loc_info}\n\n{current_error}"
                except Exception as e:
                    logger.warning(f"Pre-localization failed: {e}")

                work_result = await self.worker.dispatch(
                    current_task,
                    current_error,
                    iteration=iteration,
                    session_id=current_session_id,
                )

                if not work_result.dispatched:
                    self._circuit_breaker.record_failure()
                    error_context = work_result.error or "Dispatch failed"
                    continue

                # Extract session ID from handle for state persistence
                handle = work_result.handle
                handle_session_id = handle.handle_data.get("session_id")
                if handle_session_id:
                    current_session_id = handle_session_id

                # Log the prompt sent (if available in handle)
                if self._current_work_log_entry:
                    prompt = handle.handle_data.get("prompt")
                    if prompt:
                        self._current_work_log_entry.prompt_sent = prompt
                    if current_session_id:
                        self._current_work_log_entry.session_id = current_session_id

                # Save state immediately after dispatch
                if current_session_id:
                    self._update_state(
                        task_description=task_description,
                        iteration=iteration,
                        session_id=current_session_id,
                        work_branch=synchronizer.work_branch or "unknown",
                        error_context=error_context,
                        started_at=started_at,
                    )
                    if self._current_loop_state:
                        self._current_loop_state.save(state_file)

                # 2. POLLING via Worker
                self._transition_to(SupervisorState.POLLING)
                poll_result = await self.worker.poll(handle)

                if poll_result.status == WorkStatus.FAILED:
                    self._circuit_breaker.record_failure()
                    error_context = poll_result.error or "Worker failed"

                    # Fatal errors — abort immediately
                    if poll_result.error and (
                        "timed out" in poll_result.error.lower()
                        or "could not be found" in poll_result.error.lower()
                    ):
                        synchronizer.git.checkout(synchronizer.starting_branch)
                        self._transition_to(SupervisorState.FAILED)
                        return LoopResult.failure_result(
                            iterations=iteration,
                            started_at=started_at,
                            failure_reason=poll_result.error,
                        )
                    continue

                # 3. SYNCING via Worker
                self._transition_to(SupervisorState.SYNCING)
                sync_result = await self.worker.sync(handle, iteration)

                # Handle pending human review
                if sync_result.needs_human_review:
                    review_files = sync_result.review_required_files or []
                    pending_patch = synchronizer.patch_applier.pending_patch
                    if pending_patch:
                        approved = synchronizer.prompt_human_review(
                            review_files,
                            pending_patch,
                        )
                        if approved:
                            patch_result = synchronizer.apply_pending_patch()
                            if not patch_result.success:
                                self._circuit_breaker.record_failure()
                                if sync_result.iter_branch:
                                    synchronizer.cleanup_branch(sync_result.iter_branch)
                                error_context = (
                                    f"Patch application failed after approval: {patch_result.error}"
                                )
                                continue
                            # Update sync_result with the applied patch info
                            sync_result = sync_result.model_copy(
                                update={
                                    "success": True,
                                    "diff_hash": patch_result.diff_hash,
                                    "needs_human_review": False,
                                }
                            )
                        else:
                            self._circuit_breaker.record_failure()
                            if sync_result.iter_branch:
                                synchronizer.cleanup_branch(sync_result.iter_branch)
                            synchronizer.git.checkout(synchronizer.starting_branch)
                            self._transition_to(SupervisorState.FAILED)
                            return LoopResult.failure_result(
                                iterations=iteration,
                                started_at=started_at,
                                failure_reason="Human review rejected",
                                error_context=(
                                    f"User rejected changes to: {', '.join(review_files)}"
                                ),
                            )
                    else:
                        self._circuit_breaker.record_failure()
                        if sync_result.iter_branch:
                            synchronizer.cleanup_branch(sync_result.iter_branch)
                        error_context = "Pending review but no patch data found"
                        continue

                if not sync_result.success:
                    self._circuit_breaker.record_failure()
                    if sync_result.iter_branch:
                        synchronizer.cleanup_branch(sync_result.iter_branch)

                    # Patch failures are not recoverable - stop immediately
                    synchronizer.git.checkout(synchronizer.starting_branch)
                    self._transition_to(SupervisorState.FAILED)
                    return LoopResult.failure_result(
                        iterations=iteration,
                        started_at=started_at,
                        failure_reason="Patch failed to apply",
                        error_context=sync_result.error or "Sync failed",
                    )

                # Record diff hash for stagnation detection
                if sync_result.diff_hash:
                    self._circuit_breaker.record_diff_hash(sync_result.diff_hash)

                # Record patch summary in work log
                if self._current_work_log_entry and sync_result.patch_summary:
                    self._current_work_log_entry.patch_summary = sync_result.patch_summary

                # 4. VERIFYING
                self._transition_to(SupervisorState.VERIFYING)
                verification_result = await self.verifier.run_all()

                if verification_result.passed:
                    # 5. SUCCESS
                    self._transition_to(SupervisorState.SUCCESS)
                    assert sync_result.iter_branch is not None
                    commit_hash = synchronizer.merge_to_main(
                        sync_result.iter_branch, task_description
                    )
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
                        final_commit=commit_hash,
                        target_branch=synchronizer.work_branch,
                    )

                # 6. FAILURE (Loop)
                self._circuit_breaker.record_failure()
                error_context = await self.verifier.generate_feedback(verification_result)

                # Log failed iteration
                self._log_iteration_end(
                    session_status="completed",
                    verification_passed=False,
                    verification_errors=error_context,
                )

                # Cleanup failed branch
                if sync_result.iter_branch:
                    synchronizer.cleanup_branch(sync_result.iter_branch)

        # Loop terminated
        synchronizer.git.checkout(synchronizer.starting_branch)
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
        cost_metadata: dict[str, int | float] | None = None,
    ) -> None:
        """Log the end of an iteration to the work log.

        Args:
            session_status: Status of the Jules session
            verification_passed: Whether verification passed
            verification_errors: Error summary if verification failed
            cost_metadata: Optional dict with keys api_calls_count, estimated_tokens, vm_time_seconds
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

        # Populate cost metadata if provided
        if cost_metadata:
            if "api_calls_count" in cost_metadata:
                self._current_work_log_entry.api_calls_count = int(cost_metadata["api_calls_count"])
            if "estimated_tokens" in cost_metadata:
                self._current_work_log_entry.estimated_tokens = int(
                    cost_metadata["estimated_tokens"]
                )
            if "vm_time_seconds" in cost_metadata:
                self._current_work_log_entry.vm_time_seconds = float(
                    cost_metadata["vm_time_seconds"]
                )

        # Write to log
        try:
            self.worklog_writer.write(self._current_work_log_entry)
            logger.debug(
                f"Work log entry written for iteration {self._current_work_log_entry.iteration}"
            )
        except Exception as e:
            logger.warning(f"Failed to write work log entry: {e}")

    @staticmethod
    def _load_learned_rules_context(rules_file: Path) -> str | None:
        """Load learned rules and format them as a context string for prompts.

        Args:
            rules_file: Path to the learned rules YAML file.

        Returns:
            Formatted rules string, or None if no rules are available.
        """
        try:
            manager = RuleManager(rules_file)
            rules = manager.load()
            if not rules:
                return None
            lines = [f"- {r.rule_text}" for r in rules if r.confidence_score >= 0.3]
            return "\n".join(lines) if lines else None
        except Exception as e:
            logger.warning(f"Failed to load learned rules: {e}")
            return None

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
        try:
            synchronizer = getattr(self.worker, "synchronizer", None)
            if synchronizer is not None:
                synchronizer.git.checkout(synchronizer.starting_branch)
        except Exception as e:
            logger.warning(f"Failed to cleanup branch on shutdown: {e}")

        sys.exit(0)


class _noop_context:
    """No-op context manager for workers without a progress reporter."""

    def __enter__(self) -> "_noop_context":
        return self

    def __exit__(self, *args: object) -> None:
        pass
