import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from veridical.api.client import JulesClient
from veridical.api.models import SessionState
from veridical.dispatcher.session import Dispatcher
from veridical.models.result import LoopResult
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
    ) -> None:
        """Initialize the supervisor.

        Args:
            config: Veridical configuration
            client: Jules API client
            repo_path: Path to the repository root
        """
        self.config = config
        self.client = client
        self.repo_path = repo_path

        self._state = SupervisorState.IDLE
        self._circuit_breaker = CircuitBreaker(
            max_iterations=config.supervisor.max_iterations,
            max_consecutive_failures=config.supervisor.max_consecutive_failures,
            stagnation_threshold=config.supervisor.stagnation_threshold,
        )

        # Initialize components
        self.dispatcher = Dispatcher(config, client, repo_path)
        self.poller = Poller(config, client)
        self.synchronizer = Synchronizer(config, repo_path)
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

    async def run(self, task_description: str) -> LoopResult:
        """Run the supervisor loop for a task.

        This is the main entry point for executing an autonomous
        quality assurance loop.

        Args:
            task_description: Description of the task to perform

        Returns:
            Result of the loop execution
        """
        started_at = datetime.now()
        error_context: str | None = None

        self._circuit_breaker.reset()

        while not self._circuit_breaker.is_open:
            self._circuit_breaker.record_iteration()
            if self._circuit_breaker.is_open:
                break

            iteration = self._circuit_breaker.iteration_count
            logger.info(f"--- Starting Iteration {iteration} ---")

            # 1. DISPATCHING
            self._transition_to(SupervisorState.DISPATCHING)
            prompt = self.dispatcher.build_prompt(task_description, error_context)

            # Create session (auto-detect source)
            session = await self.dispatcher.create_session(prompt)

            # 2. POLLING
            self._transition_to(SupervisorState.POLLING)
            try:
                poll_result = await self.poller.wait_for_completion(session.session_id)
            except TimeoutError:
                self._transition_to(SupervisorState.FAILED)
                return LoopResult.failure_result(
                    iterations=iteration,
                    started_at=started_at,
                    failure_reason="Session timed out",
                )

            if poll_result.final_state == SessionState.FAILED:
                self._circuit_breaker.record_failure()
                error_context = f"Jules session {session.session_id} failed"
                continue

            # 3. SYNCING
            self._transition_to(SupervisorState.SYNCING)
            iter_branch = self.synchronizer.create_iteration_branch(iteration)

            patch_result = await self.synchronizer.apply_session_patch(
                self.client,
                session.session_id,
            )

            self._circuit_breaker.record_diff_hash(patch_result.diff_hash)

            if not patch_result.success:
                self._circuit_breaker.record_failure()
                # Clean up branch
                self.synchronizer.cleanup_branch(iter_branch)
                error_context = f"Patch application failed: {patch_result.error}"
                continue

            # 4. VERIFYING
            self._transition_to(SupervisorState.VERIFYING)
            verification_result = await self.verifier.run_all()

            if verification_result.passed:
                # 5. SUCCESS
                self._transition_to(SupervisorState.SUCCESS)
                commit_hash = self.synchronizer.merge_to_main(iter_branch)
                self._circuit_breaker.record_success()

                return LoopResult(
                    success=True,
                    iterations=iteration,
                    started_at=started_at,
                    completed_at=datetime.now(),
                    final_commit=commit_hash,
                )

            # 6. FAILURE (Loop)
            self._circuit_breaker.record_failure()
            error_context = self.verifier.generate_feedback(verification_result)

            # Cleanup failed branch to keep repo clean?
            # Or keep it for inspection?
            # Usually strict cleanup in loop, unless debug mode.
            # But we are iterating on main.
            self.synchronizer.cleanup_branch(iter_branch)

        # Loop terminated
        self._transition_to(SupervisorState.FAILED)
        return LoopResult.failure_result(
            iterations=self._circuit_breaker.iteration_count,
            started_at=started_at,
            failure_reason=self._circuit_breaker.open_reason or "Max iterations reached",
        )
