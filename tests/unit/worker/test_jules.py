import pytest
from unittest.mock import AsyncMock, Mock, patch
from veridical.worker.jules import JulesWorker
from veridical.api.client import JulesClient
from veridical.api.models import SessionState, SessionResponse
from veridical.models.result import PatchResult
from veridical.worker import WorkHandle, PollResult, SyncResult, WorkResult

@pytest.mark.unit
class TestJulesWorker:
    @pytest.fixture
    def mock_client(self):
        return AsyncMock(spec=JulesClient)

    @pytest.fixture
    def mock_config(self):
        # Need minimal config
        from veridical.config.schema import VeridicalConfig
        return VeridicalConfig()

    @pytest.fixture
    def worker(self, mock_config, mock_client, tmp_path):
        with patch("veridical.worker.jules.Dispatcher") as MockDispatcher, \
             patch("veridical.worker.jules.Poller") as MockPoller, \
             patch("veridical.worker.jules.Synchronizer") as MockSynchronizer:

            mock_dispatcher_instance = MockDispatcher.return_value
            mock_dispatcher_instance.create_session = AsyncMock()
            mock_dispatcher_instance.build_prompt = Mock() # Sync

            mock_poller_instance = MockPoller.return_value
            mock_poller_instance.wait_for_completion = AsyncMock()

            mock_synchronizer_instance = MockSynchronizer.return_value
            mock_synchronizer_instance.apply_session_patch = AsyncMock()
            mock_synchronizer_instance.merge_to_main = Mock() # Sync
            mock_synchronizer_instance.cleanup_branch = Mock() # Sync
            mock_synchronizer_instance.setup_work_branch = Mock() # Sync
            mock_synchronizer_instance.git = Mock()

            yield JulesWorker(mock_config, mock_client, tmp_path)

    @pytest.mark.asyncio
    async def test_prepare(self, worker):
        worker.synchronizer.work_branch = "work-branch"
        res = await worker.prepare("task", "target")
        worker.synchronizer.setup_work_branch.assert_called_with("task", "target")
        assert res == "work-branch"

    @pytest.mark.asyncio
    async def test_dispatch_new(self, worker):
        worker.dispatcher.build_prompt.return_value = "prompt"
        # Mock create_session return value
        session_mock = Mock()
        session_mock.session_id = "123"
        worker.dispatcher.create_session.return_value = session_mock

        res = await worker.dispatch("task")

        worker.dispatcher.build_prompt.assert_called_with("task", None)
        worker.dispatcher.create_session.assert_called()
        assert res.handle.id == "123"
        assert res.prompt_sent == "prompt"

    @pytest.mark.asyncio
    async def test_dispatch_existing(self, worker):
        worker.dispatcher.build_prompt.return_value = "prompt"
        handle = WorkHandle(id="123")

        res = await worker.dispatch("task", handle=handle)

        worker.client.send_message.assert_called_with("123", "prompt")
        assert res.handle.id == "123"

    @pytest.mark.asyncio
    async def test_poll(self, worker):
        from veridical.poller.monitor import PollResult as MonitorPollResult
        from datetime import datetime

        worker.poller.wait_for_completion.return_value = MonitorPollResult(
            session_id="123",
            final_state=SessionState.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            poll_count=1
        )

        handle = WorkHandle(id="123")
        res = await worker.poll(handle)

        assert res.handle.id == "123"
        assert res.status == "completed"
        assert res.error is None

    @pytest.mark.asyncio
    async def test_sync(self, worker):
        patch_result = PatchResult.applied([], "hash")
        worker.synchronizer.apply_session_patch.return_value = ("branch", patch_result)

        handle = WorkHandle(id="123", context={"iteration": 2})
        res = await worker.sync(handle)

        worker.synchronizer.apply_session_patch.assert_called_with(
            worker.client, "123", 2
        )
        assert res.branch_name == "branch"
        assert res.patch_result == patch_result

    @pytest.mark.asyncio
    async def test_finalize_success(self, worker):
        worker.synchronizer.merge_to_main.return_value = "commit"
        res = await worker.finalize(True, "task", "branch")
        worker.synchronizer.merge_to_main.assert_called_with("branch", "task")
        assert res == "commit"

    @pytest.mark.asyncio
    async def test_finalize_fail(self, worker):
        await worker.finalize(False, "task", "branch")
        worker.synchronizer.git.checkout.assert_called()

    @pytest.mark.asyncio
    async def test_cleanup(self, worker):
        await worker.cleanup("branch")
        worker.synchronizer.cleanup_branch.assert_called_with("branch")
        worker.synchronizer.git.checkout.assert_called()
