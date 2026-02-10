import pytest
from veridical.worker import Worker, WorkHandle, WorkResult, PollResult, SyncResult
from pathlib import Path

@pytest.mark.unit
class TestWorkerProtocol:
    def test_worker_protocol_runtime_check(self):
        """Test that Worker protocol is runtime checkable."""
        class MyWorker:
            async def prepare(self, task: str, target_branch: str | None = None, tasks_file: Path | None = None) -> str | None:
                return "branch"
            async def dispatch(self, task, error_context=None, handle=None) -> WorkResult:
                return WorkResult(handle=WorkHandle(id="1"))
            async def poll(self, handle) -> PollResult:
                return PollResult(handle=handle, status="completed", duration_seconds=1.0)
            async def sync(self, handle) -> SyncResult:
                from veridical.models.result import PatchResult
                return SyncResult(patch_result=PatchResult.applied([], "hash"))
            async def finalize(self, success, task, branch_name=None) -> str | None:
                return "commit"
            async def cleanup(self, branch_name=None) -> None:
                pass
            def cleanup_sync(self) -> None:
                pass

        assert isinstance(MyWorker(), Worker)
