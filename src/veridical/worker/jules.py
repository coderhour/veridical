"""Jules worker implementation wrapping existing Dispatcher, Poller, and Synchronizer."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from veridical.api.models import SessionState
from veridical.cli.progress import ProgressReporter
from veridical.dispatcher.session import Dispatcher
from veridical.models.result import PatchStatus
from veridical.poller.monitor import Poller
from veridical.synchronizer.patch import Synchronizer
from veridical.worker.models import (
    PollResult,
    SyncResult,
    WorkHandle,
    WorkResult,
    WorkStatus,
)

if TYPE_CHECKING:
    from veridical.api.client import JulesClient
    from veridical.config.schema import VeridicalConfig

logger = logging.getLogger(__name__)


class JulesWorker:
    """Worker implementation backed by Google Jules.

    Composes the existing Dispatcher, Poller, and Synchronizer
    components to satisfy the Worker protocol without deleting
    any existing logic.
    """

    def __init__(
        self,
        config: "VeridicalConfig",
        client: "JulesClient",
        repo_path: Path,
        *,
        verbose: bool = False,
        console: Console | None = None,
        synchronizer: Synchronizer | None = None,
    ) -> None:
        """Initialize the Jules worker.

        Args:
            config: Veridical configuration
            client: Jules API client
            repo_path: Path to the repository root
            verbose: Enable verbose output
            console: Rich console instance
            synchronizer: Optional shared Synchronizer instance (created if not provided)
        """
        self.config = config
        self.client = client
        self.repo_path = repo_path
        self.verbose = verbose
        self.console = console or Console()

        self.progress = ProgressReporter(console=self.console, verbose=self.verbose)
        self.dispatcher = Dispatcher(config, client, repo_path)
        self.poller = Poller(config, client, progress=self.progress)
        self.synchronizer = synchronizer or Synchronizer(config, repo_path, console=self.console)

    async def dispatch(
        self,
        task: str,
        error_context: str | None = None,
        *,
        iteration: int = 1,
        session_id: str | None = None,
    ) -> WorkResult:
        """Dispatch a task to Jules.

        Creates a new session on the first iteration, or sends
        feedback to an existing session on subsequent iterations.

        Args:
            task: Task description
            error_context: Error feedback from previous iteration
            iteration: Current loop iteration (1-based)
            session_id: Optional existing session ID to resume

        Returns:
            WorkResult containing a WorkHandle with the session_id
        """
        try:
            if session_id and iteration > 1:
                # Send feedback to existing session
                logger.info(f"Sending feedback to existing session: {session_id}")
                feedback_prompt = self.dispatcher.build_prompt(task, error_context)
                await self.client.send_message(session_id, feedback_prompt)
                return WorkResult(
                    handle=WorkHandle(
                        backend="jules",
                        handle_data={"session_id": session_id},
                    ),
                )
            elif session_id and iteration == 1:
                # Resume existing session — skip dispatching
                logger.info(f"Resuming existing session: {session_id}")
                return WorkResult(
                    handle=WorkHandle(
                        backend="jules",
                        handle_data={"session_id": session_id, "resumed": True},
                    ),
                )
            else:
                # First iteration — create new session
                prompt = self.dispatcher.build_prompt(task, error_context)
                session = await self.dispatcher.create_session(prompt, title=task)
                logger.info(f"Created new Jules session: {session.session_id}")
                return WorkResult(
                    handle=WorkHandle(
                        backend="jules",
                        handle_data={
                            "session_id": session.session_id,
                            "prompt": prompt,
                        },
                    ),
                )
        except Exception as e:
            logger.error(f"Jules dispatch failed: {e}")
            return WorkResult(
                handle=WorkHandle(backend="jules"),
                dispatched=False,
                error=str(e),
            )

    async def poll(self, handle: WorkHandle) -> PollResult:
        """Poll Jules for session completion.

        Args:
            handle: WorkHandle containing the session_id

        Returns:
            PollResult with terminal status
        """
        session_id = handle.handle_data["session_id"]
        try:
            poll_result = await self.poller.wait_for_completion(session_id)
            if poll_result.final_state == SessionState.FAILED:
                return PollResult(
                    status=WorkStatus.FAILED,
                    error=f"Jules session {session_id} failed",
                )
            return PollResult(status=WorkStatus.COMPLETED)
        except TimeoutError:
            return PollResult(
                status=WorkStatus.FAILED,
                error="Session timed out",
            )
        except Exception as e:
            return PollResult(
                status=WorkStatus.FAILED,
                error=str(e),
            )

    async def sync(self, handle: WorkHandle, iteration: int) -> SyncResult:
        """Download and apply the Jules patch locally.

        Args:
            handle: WorkHandle containing the session_id
            iteration: Current iteration for branch naming

        Returns:
            SyncResult with branch info and diff hash
        """
        session_id = handle.handle_data["session_id"]
        try:
            iter_branch, patch_result = await self.synchronizer.apply_session_patch(
                self.client,
                session_id,
                iteration,
            )

            # Handle pending human review
            if patch_result.status == PatchStatus.PENDING_REVIEW:
                return SyncResult(
                    success=False,
                    iter_branch=iter_branch,
                    needs_human_review=True,
                    review_required_files=patch_result.review_required_files,
                )

            if not patch_result.success:
                return SyncResult(
                    success=False,
                    iter_branch=iter_branch,
                    error=patch_result.error,
                )

            return SyncResult(
                success=True,
                iter_branch=iter_branch,
                diff_hash=patch_result.diff_hash,
                patch_summary=patch_result.patch_summary,
            )
        except Exception as e:
            logger.error(f"Jules sync failed: {e}")
            return SyncResult(success=False, error=str(e))
