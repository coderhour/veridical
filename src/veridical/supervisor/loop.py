import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from veridical.api.client import JulesClient
from veridical.api.exceptions import APIError
from veridical.api.models import SessionState
from veridical.cli.progress import ProgressReporter
from veridical.dispatcher.session import Dispatcher
from veridical.models.result import LoopResult, PatchStatus
from veridical.poller.monitor import Poller
from veridical.supervisor.circuit_breaker import CircuitBreaker
from veridical.supervisor.state import SupervisorState
from veridical.synchronizer.patch import Synchronizer
from veridical.verifier.quality_gate import Verifier

if TYPE_CHECKING:
    from veridical.config.schema import VeridicalConfig

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
        client: JulesClient,
        repo_path: Path,
        *,
        verbose: bool = False,
        console: Console | None = None,
    ) -> None:
        """Initialize the supervisor.

        Args:
            config: Veridical configuration
            client: Jules API client
            repo_path: Path to the repository root
            verbose: Enable verbose output
            console: Rich console instance
        """
        self.config = config
        self.client = client
        self.repo_path = repo_path
        self.verbose = verbose
        self.console = console or Console()

        self._state = SupervisorState.IDLE
        self._circuit_breaker = CircuitBreaker(
            max_iterations=config.supervisor.max_iterations,
            max_consecutive_failures=config.supervisor.max_consecutive_failures,
            stagnation_threshold=config.supervisor.stagnation_threshold,
        )

        # Initialize components
        self.progress = ProgressReporter(console=self.console, verbose=self.verbose)
        self.dispatcher = Dispatcher(config, client, repo_path)
        self.poller = Poller(config, client, progress=self.progress)
        self.synchronizer = Synchronizer(config, repo_path, console=self.console)
        self.verifier = Verifier(config, repo_path)

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
        # Update verifier and dispatcher with the tasks file if provided
        if tasks_file:
            self.verifier.current_tasks_file = tasks_file
            self.dispatcher.current_tasks_file = tasks_file

        # Set up work branch for this run
        self.synchronizer.setup_work_branch(task_description, target_branch)

        started_at = datetime.now()
        error_context: str | None = None

        self._circuit_breaker.reset()

        # Track the current session across iterations to reuse it
        current_session_id: str | None = session_id

        with self.progress:
            while not self._circuit_breaker.is_open:
                self._circuit_breaker.record_iteration()
                if self._circuit_breaker.is_open:
                    break

                iteration = self._circuit_breaker.iteration_count
                logger.info(f"--- Starting Iteration {iteration} ---")
                self.progress.set_iterations(iteration, self.config.supervisor.max_iterations)

                # 1. DISPATCHING or SENDING FEEDBACK
                if current_session_id and iteration == 1 and session_id:
                    # Resume existing session - skip dispatching
                    self.progress.set_state("Resuming session...")
                    logger.info(f"Resuming existing session: {current_session_id}")
                elif current_session_id and iteration > 1:
                    # Send feedback to existing session instead of creating new one
                    self._transition_to(SupervisorState.DISPATCHING)
                    self.progress.set_state("Sending feedback...")
                    logger.info(f"Sending feedback to existing session: {current_session_id}")

                    feedback_prompt = self.dispatcher.build_prompt(task_description, error_context)
                    await self.client.send_message(current_session_id, feedback_prompt)
                else:
                    # First iteration - create new session
                    self._transition_to(SupervisorState.DISPATCHING)
                    self.progress.set_state("Creating session...")
                    prompt = self.dispatcher.build_prompt(task_description, error_context)

                    # Create session (auto-detect source)
                    session = await self.dispatcher.create_session(prompt, title=task_description)
                    current_session_id = session.session_id

                # 2. POLLING
                self._transition_to(SupervisorState.POLLING)
                self.progress.set_state("Polling for updates...")
                try:
                    assert current_session_id is not None
                    poll_result = await self.poller.wait_for_completion(current_session_id)
                except TimeoutError:
                    self.synchronizer.git.checkout(self.synchronizer.starting_branch)
                    self._transition_to(SupervisorState.FAILED)
                    return LoopResult.failure_result(
                        iterations=iteration,
                        started_at=started_at,
                        failure_reason="Session timed out",
                    )
                except APIError as e:
                    # Handle API errors (e.g., invalid session ID returns 404)
                    self.synchronizer.git.checkout(self.synchronizer.starting_branch)
                    self._transition_to(SupervisorState.FAILED)

                    # Provide clear message for resumed sessions
                    if session_id and iteration == 1:
                        return LoopResult.failure_result(
                            iterations=iteration,
                            started_at=started_at,
                            failure_reason="Invalid session ID",
                            error_context=(
                                f"The session ID '{session_id}' could not be found. "
                                "Please verify the session ID is correct and try again.\n\n"
                                f"API Error: {e}"
                            ),
                        )

                    return LoopResult.failure_result(
                        iterations=iteration,
                        started_at=started_at,
                        failure_reason="API error during polling",
                        error_context=str(e),
                    )

                if poll_result.final_state == SessionState.FAILED:
                    self._circuit_breaker.record_failure()
                    error_context = f"Jules session {current_session_id} failed"
                    continue

                # 3. SYNCING
                self._transition_to(SupervisorState.SYNCING)
                self.progress.set_state("Applying patch...")
                iter_branch = self.synchronizer.create_iteration_branch(iteration)

                patch_result = await self.synchronizer.apply_session_patch(
                    self.client,
                    current_session_id,
                )

                # Handle pending human review
                if patch_result.status == PatchStatus.PENDING_REVIEW:
                    self.progress.set_state("Awaiting human review...")
                    logger.info(
                        f"Files requiring human review: {patch_result.review_required_files}"
                    )

                    # Prompt user for approval
                    pending_patch = self.synchronizer.patch_applier.pending_patch
                    if pending_patch:
                        approved = self.synchronizer.prompt_human_review(
                            patch_result.review_required_files,
                            pending_patch,
                        )

                        if approved:
                            # Apply the pending patch now that it's approved
                            patch_result = self.synchronizer.apply_pending_patch()
                            if not patch_result.success:
                                self._circuit_breaker.record_failure()
                                self.synchronizer.cleanup_branch(iter_branch)
                                error_context = (
                                    f"Patch application failed after approval: {patch_result.error}"
                                )
                                continue
                        else:
                            # User rejected the changes
                            self._circuit_breaker.record_failure()
                            self.synchronizer.cleanup_branch(iter_branch)
                            self.synchronizer.git.checkout(self.synchronizer.starting_branch)
                            self._transition_to(SupervisorState.FAILED)
                            return LoopResult.failure_result(
                                iterations=iteration,
                                started_at=started_at,
                                failure_reason="Human review rejected",
                                error_context=(
                                    f"User rejected changes to: "
                                    f"{', '.join(patch_result.review_required_files)}"
                                ),
                            )
                    else:
                        # No pending patch stored - unexpected state
                        self._circuit_breaker.record_failure()
                        self.synchronizer.cleanup_branch(iter_branch)
                        error_context = "Pending review but no patch data found"
                        continue

                if not patch_result.success:
                    self._circuit_breaker.record_failure()
                    # Clean up branch
                    self.synchronizer.cleanup_branch(iter_branch)

                    # If this was a resumed session, abort instead of retrying
                    # The patch was created against a different codebase version
                    if session_id and iteration == 1:
                        self.synchronizer.git.checkout(self.synchronizer.starting_branch)
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

                    error_context = f"Patch application failed: {patch_result.error}"
                    continue

                # diff_hash is always set when patch is successfully applied
                assert patch_result.diff_hash is not None
                self._circuit_breaker.record_diff_hash(patch_result.diff_hash)

                # 4. VERIFYING
                self._transition_to(SupervisorState.VERIFYING)
                self.progress.set_state("Running quality gates...")
                verification_result = await self.verifier.run_all()

                if verification_result.passed:
                    # 5. SUCCESS
                    self._transition_to(SupervisorState.SUCCESS)
                    self.progress.set_state("Merging changes...")
                    commit_hash = self.synchronizer.merge_to_main(iter_branch, task_description)
                    self._circuit_breaker.record_success()

                    return LoopResult.success_result(
                        iterations=iteration,
                        started_at=started_at,
                        final_commit=commit_hash,
                        target_branch=self.synchronizer.work_branch,
                    )

                # 6. FAILURE (Loop)
                self._circuit_breaker.record_failure()
                self.progress.set_state("Compiling feedback...")
                error_context = await self.verifier.generate_feedback(verification_result)

                # Cleanup failed branch to keep repo clean?
                # Or keep it for inspection?
                # Usually strict cleanup in loop, unless debug mode.
                # But we are iterating on main.
                self.synchronizer.cleanup_branch(iter_branch)

        # Loop terminated
        self.synchronizer.git.checkout(self.synchronizer.starting_branch)
        self._transition_to(SupervisorState.FAILED)
        return LoopResult.failure_result(
            iterations=self._circuit_breaker.iteration_count,
            started_at=started_at,
            failure_reason=self._circuit_breaker.open_reason or "Max iterations reached",
        )
