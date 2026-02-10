import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from veridical.api.client import JulesClient
from veridical.api.models import SessionState
from veridical.dispatcher.session import Dispatcher
from veridical.models.result import PatchResult, PatchStatus
from veridical.poller.monitor import Poller
from veridical.synchronizer.patch import Synchronizer
from veridical.worker import PollResult, SyncResult, WorkHandle, WorkResult

if TYPE_CHECKING:
    from veridical.cli.progress import ProgressReporter
    from veridical.config.schema import VeridicalConfig

logger = logging.getLogger(__name__)


class JulesWorker:
    """Worker implementation using Jules API."""

    def __init__(
        self,
        config: "VeridicalConfig",
        client: JulesClient,
        repo_path: Path,
        console: Console | None = None,
        progress_reporter: "ProgressReporter | None" = None,
    ) -> None:
        self.config = config
        self.client = client
        self.repo_path = repo_path
        self.console = console or Console()
        self.progress_reporter = progress_reporter

        self.dispatcher = Dispatcher(config, client, repo_path)
        self.poller = Poller(config, client, progress=progress_reporter)
        self.synchronizer = Synchronizer(config, repo_path, console=self.console)

    def set_progress_reporter(self, reporter: "ProgressReporter") -> None:
        """Set the progress reporter for UI updates."""
        self.progress_reporter = reporter
        self.poller.progress = reporter

    async def prepare(
        self,
        task: str,
        target_branch: str | None = None,
        tasks_file: Path | None = None,
    ) -> str | None:
        """Prepare the environment."""
        if tasks_file:
            self.dispatcher.current_tasks_file = tasks_file

        self.synchronizer.setup_work_branch(task, target_branch)
        return self.synchronizer.work_branch

    async def dispatch(
        self,
        task: str,
        error_context: str | None = None,
        handle: WorkHandle | None = None,
    ) -> WorkResult:
        """Dispatch a task to Jules."""
        session_id = handle.id if handle else None
        prompt_sent: str | None = None

        if session_id:
            # Send feedback to existing session
            logger.info(f"Sending feedback to existing session: {session_id}")
            prompt = self.dispatcher.build_prompt(task, error_context)
            await self.client.send_message(session_id, prompt)
            prompt_sent = prompt

            # Update handle context if needed?
            new_handle = handle or WorkHandle(id=session_id)
        else:
            # Create new session
            logger.info("Creating new Jules session")
            prompt = self.dispatcher.build_prompt(task, error_context)
            session = await self.dispatcher.create_session(prompt, title=task)
            session_id = session.session_id
            prompt_sent = prompt

            new_handle = WorkHandle(id=session_id)

        return WorkResult(handle=new_handle, prompt_sent=prompt_sent)

    async def poll(self, handle: WorkHandle) -> PollResult:
        """Wait for Jules session to complete."""
        session_id = handle.id

        # Use existing Poller logic which handles backoff, timeouts, and activities
        # Note: monitor.PollResult is different from worker.PollResult, so we map it.
        monitor_result = await self.poller.wait_for_completion(session_id)

        status = "completed"
        error = None

        if monitor_result.final_state == SessionState.FAILED:
            status = "failed"
            error = "Session failed"
        elif monitor_result.final_state == SessionState.AWAITING_USER_FEEDBACK:
            # Should not happen if poller handles it, but if it does, it's a form of completion/stop
            status = "awaiting_input"

        # We could map other states if needed

        return PollResult(
            handle=handle,
            status=status,
            error=error,
            duration_seconds=monitor_result.duration_seconds,
        )

    async def sync(self, handle: WorkHandle) -> SyncResult:
        """Sync changes from Jules session."""
        session_id = handle.id

        # We rely on handle context for iteration number
        iteration = handle.context.get("iteration", 1)

        iter_branch, patch_result = await self.synchronizer.apply_session_patch(
            self.client,
            session_id,
            iteration,
        )

        # Handle interactive review if needed
        if patch_result.status == PatchStatus.PENDING_REVIEW:
            if self.progress_reporter:
                self.progress_reporter.set_state("Awaiting human review...")
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
                    # If failed after approval, we return the failed result
                else:
                    # User rejected the changes
                    # We cleanup and return a failure result
                    self.synchronizer.cleanup_branch(iter_branch)

                    # We need to construct a rejected result
                    patch_result = PatchResult.failed(
                        error=f"User rejected changes to: {', '.join(patch_result.review_required_files)}",
                        status=PatchStatus.REJECTED,
                    )
            else:
                # Should not happen
                pass

        return SyncResult(
            patch_result=patch_result,
            branch_name=iter_branch,
        )

    async def finalize(
        self, success: bool, task: str, branch_name: str | None = None
    ) -> str | None:
        """Finalize the work."""
        if success and branch_name:
            # Merge iteration branch to work branch
            commit = self.synchronizer.merge_to_main(branch_name, task)
            return commit

        # If failure or no branch, ensure we are on starting branch
        if not success:
            self.synchronizer.git.checkout(self.synchronizer.starting_branch)

        return None

    async def cleanup(self, branch_name: str | None = None) -> None:
        """Cleanup environment."""
        if branch_name:
            self.synchronizer.cleanup_branch(branch_name)

        # Also ensure we are on starting branch if we are shutting down?
        with contextlib.suppress(Exception):
            self.synchronizer.git.checkout(self.synchronizer.starting_branch)

    def cleanup_sync(self) -> None:
        """Synchronous cleanup for signal handlers."""
        # This is safe because Git operations in Synchronizer are synchronous
        try:
            self.synchronizer.git.checkout(self.synchronizer.starting_branch)
        except Exception as e:
            logger.warning(f"Failed to cleanup branch on shutdown: {e}")
