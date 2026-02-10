"""Worker protocol definition using structural subtyping."""

from typing import Protocol, runtime_checkable

from veridical.worker.models import PollResult, SyncResult, WorkHandle, WorkResult


@runtime_checkable
class Worker(Protocol):
    """Protocol for AI worker backends.

    Any class implementing dispatch(), poll(), and sync() with
    matching signatures satisfies this protocol via structural
    subtyping — no inheritance required.
    """

    async def dispatch(
        self,
        task: str,
        error_context: str | None = None,
        *,
        iteration: int = 1,
        session_id: str | None = None,
    ) -> WorkResult:
        """Dispatch a task to the worker backend.

        On the first iteration this creates a new work session.
        On subsequent iterations it sends feedback (error_context)
        to an existing session identified by the handle inside
        session_id / previous WorkResult.

        Args:
            task: Task description / prompt
            error_context: Error feedback from the previous iteration
            iteration: Current loop iteration (1-based)
            session_id: Optional existing session to resume

        Returns:
            WorkResult with a handle for polling and syncing
        """
        ...

    async def poll(self, handle: WorkHandle) -> PollResult:
        """Poll the worker for completion status.

        Blocks (with internal backoff) until the work reaches a
        terminal state or times out.

        Args:
            handle: Opaque handle from dispatch()

        Returns:
            PollResult with current status
        """
        ...

    async def sync(self, handle: WorkHandle, iteration: int) -> SyncResult:
        """Synchronize the worker's output to the local repository.

        For Jules this downloads the patch and applies it to an
        iteration branch. For local workers this may be a no-op.

        Args:
            handle: Opaque handle from dispatch()
            iteration: Current loop iteration (for branch naming)

        Returns:
            SyncResult with branch info and diff hash
        """
        ...
