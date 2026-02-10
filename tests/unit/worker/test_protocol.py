"""Tests for Worker protocol compliance."""

from unittest.mock import AsyncMock

import pytest

from veridical.worker.models import PollResult, SyncResult, WorkHandle, WorkResult, WorkStatus
from veridical.worker.protocol import Worker


class ConcreteWorker:
    """Minimal concrete implementation of the Worker protocol for testing."""

    async def dispatch(
        self,
        task: str,
        _error_context: str | None = None,
        *,
        _iteration: int = 1,
        _session_id: str | None = None,
    ) -> WorkResult:
        return WorkResult(
            handle=WorkHandle(backend="test", handle_data={"task": task}),
        )

    async def poll(self, _handle: WorkHandle) -> PollResult:
        return PollResult(status=WorkStatus.COMPLETED)

    async def sync(self, _handle: WorkHandle, iteration: int) -> SyncResult:
        return SyncResult(success=True, iter_branch=f"iter-{iteration}", diff_hash="abc")


class IncompleteWorker:
    """A class that does NOT satisfy the Worker protocol (missing sync)."""

    async def dispatch(self, _task: str, _error_context: str | None = None) -> WorkResult:
        return WorkResult(
            handle=WorkHandle(backend="test"),
        )

    async def poll(self, _handle: WorkHandle) -> PollResult:
        return PollResult(status=WorkStatus.COMPLETED)


@pytest.mark.unit
class TestWorkerProtocol:
    """Tests for Worker protocol structural subtyping."""

    def test_concrete_worker_satisfies_protocol(self) -> None:
        """A class implementing all three methods satisfies the protocol."""
        worker = ConcreteWorker()
        assert isinstance(worker, Worker)

    def test_async_mock_satisfies_protocol(self) -> None:
        """An AsyncMock satisfies the protocol (duck typing)."""
        mock_worker = AsyncMock()
        assert isinstance(mock_worker, Worker)

    @pytest.mark.asyncio
    async def test_concrete_worker_dispatch(self) -> None:
        """ConcreteWorker.dispatch returns a valid WorkResult."""
        worker = ConcreteWorker()
        result = await worker.dispatch("test task")
        assert result.dispatched is True
        assert result.handle.backend == "test"

    @pytest.mark.asyncio
    async def test_concrete_worker_poll(self) -> None:
        """ConcreteWorker.poll returns a valid PollResult."""
        worker = ConcreteWorker()
        handle = WorkHandle(backend="test", handle_data={})
        result = await worker.poll(handle)
        assert result.status == WorkStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_concrete_worker_sync(self) -> None:
        """ConcreteWorker.sync returns a valid SyncResult."""
        worker = ConcreteWorker()
        handle = WorkHandle(backend="test", handle_data={})
        result = await worker.sync(handle, iteration=1)
        assert result.success is True
        assert result.iter_branch == "iter-1"
