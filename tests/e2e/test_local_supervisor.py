"""E2E tests for the Local Supervisor loop."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from veridical.config.schema import LocalConfig
from veridical.local.providers.registry import LocalProviderRegistry
from veridical.local.supervisor import LocalSupervisor


@pytest.mark.e2e
class TestLocalSupervisorE2E:
    """End-to-end tests for Local Supervisor."""

    @pytest.mark.asyncio
    async def test_local_max_iterations_exceeded(self, e2e_temp_repo, e2e_config):
        """Test that local loop circuit breaker trips after max_iterations (Task 3.2)."""
        e2e_config.supervisor.max_iterations = 2

        # Create a worker script that does nothing (verification will always fail)
        worker_script = e2e_temp_repo / "worker.sh"
        worker_script.write_text("#!/bin/bash\necho 'doing nothing'\n")
        worker_script.chmod(0o755)

        e2e_config.local = LocalConfig(worker_command=f"bash {worker_script}", mode="subprocess")

        supervisor = LocalSupervisor(e2e_config, e2e_temp_repo)

        # Mock verifier to always fail
        supervisor.verifier.run_all = AsyncMock(
            return_value=MagicMock(passed=False, gate_results=[])
        )
        supervisor.verifier.generate_feedback = AsyncMock(return_value="Still failing")

        result = await supervisor.run("Task that always fails")

        assert result.success is False
        assert "Maximum iterations exceeded" in result.failure_reason
        assert result.iterations == 2

    @pytest.mark.asyncio
    async def test_local_provider_command_construction(self, e2e_temp_repo, e2e_config):
        """Test: local loop with provider-based command construction (Task 3.3)."""

        # Register a mock provider
        class MockProvider:
            name = "mock-tool"
            description = "Mock coding tool"

            def build_command(self, task, error_context=None, mode="subprocess"):
                _ = mode
                cmd = f"echo '{task}'"
                if error_context:
                    cmd += f" --feedback '{error_context}'"
                return cmd

            def default_mode(self):
                return "subprocess"

            def detect(self):
                return True

        LocalProviderRegistry.register("mock-tool", MockProvider)

        try:
            # Manually resolve provider as the CLI would do
            provider_cls = LocalProviderRegistry.resolve("mock-tool")
            provider = provider_cls()

            e2e_config.local = LocalConfig(provider="mock-tool")

            # We must use create_subprocess_shell mock if LocalRunner uses it
            with patch("asyncio.create_subprocess_shell") as mock_shell:
                # Mock process
                mock_process = AsyncMock()
                mock_process.communicate.return_value = (b"done", b"")
                mock_process.returncode = 0
                mock_shell.return_value = mock_process

                supervisor = LocalSupervisor(e2e_config, e2e_temp_repo, provider=provider)
                supervisor.verifier.run_all = AsyncMock(return_value=MagicMock(passed=True))

                await supervisor.run("Build a widget")

                # Check that mock_shell was called with command from provider
                args, _kwargs = mock_shell.call_args
                assert "echo 'Build a widget'" in args[0]
        finally:
            pass

    @pytest.mark.asyncio
    async def test_local_worklog_written(self, e2e_temp_repo, e2e_config):
        """Test that local loop worklog entries are written during run (Task 3.4)."""
        # Mock successful run
        worker_script = e2e_temp_repo / "worker.sh"
        worker_script.write_text("#!/bin/bash\necho 'done'\n")
        worker_script.chmod(0o755)

        e2e_config.local = LocalConfig(worker_command=f"bash {worker_script}")
        e2e_config.worklog.enabled = True

        supervisor = LocalSupervisor(e2e_config, e2e_temp_repo)
        supervisor.verifier.run_all = AsyncMock(return_value=MagicMock(passed=True))

        await supervisor.run("Log this task")

        date_str = datetime.now().strftime("%Y-%m-%d")
        worklog_file = e2e_temp_repo / "worklog" / date_str / "iterations.jsonl"

        assert worklog_file.exists()
        lines = worklog_file.read_text().splitlines()
        assert len(lines) > 0

        # Verify first entry
        first_entry = json.loads(lines[0])
        assert first_entry["iteration"] == 1
        assert first_entry["session_id"] == "local"
