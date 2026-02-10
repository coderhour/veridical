"""Integration tests for Supervisor components interaction."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from veridical.config.schema import LocalConfig
from veridical.local.supervisor import LocalSupervisor
from veridical.synchronizer.patch import Synchronizer


@pytest.mark.integration
class TestSupervisorComponents:
    """Tests integrating multiple components without full E2E mocking."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_local_integration(self, e2e_temp_repo, sample_config_path):
        """Test: CircuitBreaker integrates correctly with LocalSupervisor (Task 5.11)."""
        from veridical.config.loader import load_config

        config = load_config(sample_config_path)
        config.supervisor.max_iterations = 2
        config.local = LocalConfig(worker_command="echo 'fixed' > code.txt", mode="subprocess")

        supervisor = LocalSupervisor(config, e2e_temp_repo)

        call_count = 0

        async def mock_run_all():
            nonlocal call_count
            call_count += 1
            return MagicMock(passed=False)

        supervisor.verifier.run_all = mock_run_all
        supervisor.verifier.generate_feedback = AsyncMock(return_value="Fail")

        result = await supervisor.run("Task")

        assert result.success is False
        assert "Maximum iterations exceeded" in result.failure_reason
        assert result.iterations == 2
        # Use _circuit_breaker since property doesn't exist on LocalSupervisor
        assert supervisor._circuit_breaker.iteration_count == 3

    def test_synchronizer_branch_lifecycle(self, e2e_temp_repo, e2e_config):
        """Test: Synchronizer creates and cleans up iteration branches correctly (Task 5.12)."""
        e2e_config.git.auto_create_work_branch = True
        sync = Synchronizer(e2e_config, e2e_temp_repo)

        # 1. Setup work branch
        sync.setup_work_branch("test-task")
        work_branch = sync.work_branch
        assert work_branch.startswith("feat/test-task")

        # 2. Create iteration branch
        iter_branch = sync.create_iteration_branch(1)
        assert iter_branch == "veridical/iter-1"

        # Check git branches
        import subprocess

        result = subprocess.run(
            ["git", "branch"], cwd=e2e_temp_repo, capture_output=True, text=True
        )
        assert iter_branch in result.stdout

        # 3. Cleanup iteration branch
        sync.cleanup_branch(iter_branch)
        result = subprocess.run(
            ["git", "branch"], cwd=e2e_temp_repo, capture_output=True, text=True
        )
        assert iter_branch not in result.stdout
        assert work_branch in result.stdout

        # 4. Cleanup work branch
        # Reset base_branch to main so we can checkout main before deleting work_branch
        sync.branch_manager.base_branch = "main"
        sync.cleanup_branch(work_branch)
        result = subprocess.run(
            ["git", "branch"], cwd=e2e_temp_repo, capture_output=True, text=True
        )
        assert work_branch not in result.stdout
