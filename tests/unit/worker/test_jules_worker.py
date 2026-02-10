"""Tests for JulesWorker implementation."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from veridical.api.models import SessionState
from veridical.models.result import PatchResult, PatchStatus
from veridical.worker.jules import JulesWorker
from veridical.worker.models import WorkHandle, WorkStatus
from veridical.worker.protocol import Worker


@pytest.mark.unit
class TestJulesWorker:
    """Tests for JulesWorker."""

    @pytest.fixture
    def mock_config(self) -> MagicMock:
        config = MagicMock()
        config.jules.api_base_url = "https://test.example.com"
        config.jules.poll_interval = 1
        config.jules.poll_timeout = 60
        config.jules.auto_approve_plans = True
        config.jules.backoff.type = "constant"
        config.jules.backoff.interval = 0.1
        return config

    @pytest.fixture
    def mock_client(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def worker(self, mock_config: MagicMock, mock_client: AsyncMock, tmp_path: Path) -> JulesWorker:
        with (
            patch("veridical.synchronizer.patch.GitWrapper"),
            patch("veridical.synchronizer.branch.GitWrapper"),
        ):
            return JulesWorker(mock_config, mock_client, tmp_path)

    def test_satisfies_worker_protocol(self, worker: JulesWorker) -> None:
        """JulesWorker satisfies the Worker protocol."""
        assert isinstance(worker, Worker)

    def test_exposes_synchronizer(self, worker: JulesWorker) -> None:
        """JulesWorker exposes a synchronizer attribute."""
        assert worker.synchronizer is not None

    def test_exposes_dispatcher(self, worker: JulesWorker) -> None:
        """JulesWorker exposes a dispatcher attribute."""
        assert worker.dispatcher is not None

    @pytest.mark.asyncio
    async def test_dispatch_creates_new_session(self, worker: JulesWorker) -> None:
        """First dispatch creates a new Jules session."""
        mock_session = MagicMock()
        mock_session.session_id = "new-sess-123"
        worker.dispatcher.create_session = AsyncMock(return_value=mock_session)
        worker.dispatcher.build_prompt = MagicMock(return_value="test prompt")

        result = await worker.dispatch("Fix bug", iteration=1)

        assert result.dispatched is True
        assert result.handle.backend == "jules"
        assert result.handle.handle_data["session_id"] == "new-sess-123"
        worker.dispatcher.create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_resumes_existing_session(self, worker: JulesWorker) -> None:
        """Dispatch with session_id and iteration=1 resumes without creating."""
        result = await worker.dispatch("Continue", iteration=1, session_id="existing-123")

        assert result.dispatched is True
        assert result.handle.handle_data["session_id"] == "existing-123"
        assert result.handle.handle_data.get("resumed") is True

    @pytest.mark.asyncio
    async def test_dispatch_sends_feedback(self, worker: JulesWorker) -> None:
        """Dispatch with session_id and iteration>1 sends feedback."""
        worker.dispatcher.build_prompt = MagicMock(return_value="feedback prompt")

        result = await worker.dispatch(
            "Fix bug", "error output", iteration=2, session_id="sess-123"
        )

        assert result.dispatched is True
        assert result.handle.handle_data["session_id"] == "sess-123"
        worker.client.send_message.assert_called_once_with("sess-123", "feedback prompt")

    @pytest.mark.asyncio
    async def test_dispatch_failure_returns_error(self, worker: JulesWorker) -> None:
        """Dispatch failure returns WorkResult with dispatched=False."""
        worker.dispatcher.build_prompt = MagicMock(side_effect=RuntimeError("boom"))

        result = await worker.dispatch("Fix bug", iteration=1)

        assert result.dispatched is False
        assert "boom" in result.error

    @pytest.mark.asyncio
    async def test_poll_completed(self, worker: JulesWorker) -> None:
        """Poll returns COMPLETED when session finishes."""
        poll_result = MagicMock()
        poll_result.final_state = SessionState.COMPLETED
        worker.poller.wait_for_completion = AsyncMock(return_value=poll_result)

        handle = WorkHandle(backend="jules", handle_data={"session_id": "sess-1"})
        result = await worker.poll(handle)

        assert result.status == WorkStatus.COMPLETED
        assert result.error is None

    @pytest.mark.asyncio
    async def test_poll_failed(self, worker: JulesWorker) -> None:
        """Poll returns FAILED when session fails."""
        poll_result = MagicMock()
        poll_result.final_state = SessionState.FAILED
        worker.poller.wait_for_completion = AsyncMock(return_value=poll_result)

        handle = WorkHandle(backend="jules", handle_data={"session_id": "sess-1"})
        result = await worker.poll(handle)

        assert result.status == WorkStatus.FAILED

    @pytest.mark.asyncio
    async def test_poll_timeout(self, worker: JulesWorker) -> None:
        """Poll returns FAILED on timeout."""
        worker.poller.wait_for_completion = AsyncMock(side_effect=TimeoutError())

        handle = WorkHandle(backend="jules", handle_data={"session_id": "sess-1"})
        result = await worker.poll(handle)

        assert result.status == WorkStatus.FAILED
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_sync_success(self, worker: JulesWorker) -> None:
        """Sync applies patch and returns branch info."""
        patch_result = PatchResult.applied(files_changed=["test.py"], diff_hash="abc123")
        worker.synchronizer.apply_session_patch = AsyncMock(return_value=("iter-1", patch_result))

        handle = WorkHandle(backend="jules", handle_data={"session_id": "sess-1"})
        result = await worker.sync(handle, iteration=1)

        assert result.success is True
        assert result.iter_branch == "iter-1"
        assert result.diff_hash == "abc123"

    @pytest.mark.asyncio
    async def test_sync_failure(self, worker: JulesWorker) -> None:
        """Sync returns failure when patch fails."""
        patch_result = PatchResult.failed(error="patch does not apply")
        worker.synchronizer.apply_session_patch = AsyncMock(return_value=("iter-1", patch_result))

        handle = WorkHandle(backend="jules", handle_data={"session_id": "sess-1"})
        result = await worker.sync(handle, iteration=1)

        assert result.success is False
        assert result.error == "patch does not apply"

    @pytest.mark.asyncio
    async def test_sync_pending_review(self, worker: JulesWorker) -> None:
        """Sync returns needs_human_review when patch requires review."""
        patch_result = PatchResult(
            success=False,
            status=PatchStatus.PENDING_REVIEW,
            review_required_files=["sensitive.py"],
        )
        worker.synchronizer.apply_session_patch = AsyncMock(return_value=("iter-1", patch_result))

        handle = WorkHandle(backend="jules", handle_data={"session_id": "sess-1"})
        result = await worker.sync(handle, iteration=1)

        assert result.needs_human_review is True
        assert result.review_required_files == ["sensitive.py"]

    @pytest.mark.asyncio
    async def test_sync_exception(self, worker: JulesWorker) -> None:
        """Sync returns failure on unexpected exception."""
        worker.synchronizer.apply_session_patch = AsyncMock(side_effect=RuntimeError("git error"))

        handle = WorkHandle(backend="jules", handle_data={"session_id": "sess-1"})
        result = await worker.sync(handle, iteration=1)

        assert result.success is False
        assert "git error" in result.error
