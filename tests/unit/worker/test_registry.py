import pytest
from unittest.mock import AsyncMock, patch
from veridical.worker.registry import WorkerRegistry
from veridical.worker.jules import JulesWorker
from veridical.config.schema import VeridicalConfig

@pytest.mark.unit
class TestWorkerRegistry:
    def test_get_worker_class_jules(self):
        cls = WorkerRegistry.get_worker_class("jules")
        assert cls == JulesWorker

    def test_get_worker_class_invalid(self):
        with pytest.raises(ValueError, match="Unknown worker backend"):
            WorkerRegistry.get_worker_class("unknown")

    def test_create_worker_jules(self):
        config = VeridicalConfig()
        config.worker.backend = "jules"
        client = AsyncMock()

        with patch("veridical.worker.jules.Dispatcher"), \
             patch("veridical.worker.jules.Poller"), \
             patch("veridical.worker.jules.Synchronizer"):

            worker = WorkerRegistry.create_worker(
                config,
                client=client,
                repo_path="path",
                console=None
            )
            assert isinstance(worker, JulesWorker)
