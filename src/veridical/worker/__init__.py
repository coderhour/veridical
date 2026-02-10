from typing import Any, Protocol, runtime_checkable
from pathlib import Path

from pydantic import BaseModel, Field

from veridical.models.result import PatchResult


class WorkHandle(BaseModel):
    """Handle for a unit of work (e.g., a session)."""

    id: str = Field(..., description="Unique identifier for the work unit")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class WorkResult(BaseModel):
    """Result of dispatching work."""

    handle: WorkHandle
    prompt_sent: str | None = Field(None, description="The prompt sent to the worker")


class PollResult(BaseModel):
    """Result of polling for work completion."""

    handle: WorkHandle
    status: str = Field(
        ...,
        description="Final status of the work (e.g., 'completed', 'failed', 'timeout')",
    )
    error: str | None = Field(None, description="Error message if failed")
    duration_seconds: float = Field(..., description="Duration of the work/polling in seconds")


class SyncResult(BaseModel):
    """Result of syncing work to local environment."""

    patch_result: PatchResult
    branch_name: str | None = Field(None, description="Name of the branch created/updated")


class WorkerConfig(BaseModel):
    """Base configuration for a worker."""

    backend: str = Field(..., description="Backend identifier (e.g., 'jules')")


@runtime_checkable
class Worker(Protocol):
    """Protocol for a worker that executes tasks."""

    async def prepare(
        self,
        task: str,
        target_branch: str | None = None,
        tasks_file: Path | None = None
    ) -> str | None:
        """Prepare the environment for work.

        Returns:
            Name of the work branch or context identifier.
        """
        ...

    async def dispatch(
        self,
        task: str,
        error_context: str | None = None,
        handle: WorkHandle | None = None,
    ) -> WorkResult:
        """Dispatch a task to the worker.

        Args:
            task: Description of the task.
            error_context: Optional error context from previous iteration.
            handle: Optional handle to existing work (for continuing/resuming).

        Returns:
            Result containing the work handle.
        """
        ...

    async def poll(self, handle: WorkHandle) -> PollResult:
        """Wait for the work to complete.

        Args:
            handle: Handle to the work unit.

        Returns:
            Result of the polling operation.
        """
        ...

    async def sync(self, handle: WorkHandle) -> SyncResult:
        """Sync the work results to the local environment.

        Args:
            handle: Handle to the work unit.

        Returns:
            Result of the sync operation.
        """
        ...

    async def finalize(
        self, success: bool, task: str, branch_name: str | None = None
    ) -> str | None:
        """Finalize the work (e.g. merge branch).

        Args:
            success: Whether the work was successful.
            task: Task description for commit messages.
            branch_name: Optional branch name to merge.

        Returns:
            Commit hash or final identifier if successful.
        """
        ...

    async def cleanup(self, branch_name: str | None = None) -> None:
        """Cleanup environment (e.g. return to original branch)."""
        ...

    def cleanup_sync(self) -> None:
        """Synchronous best-effort cleanup (for signal handlers)."""
        ...
