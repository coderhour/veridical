"""E2E tests for the Jules-based Supervisor loop."""

import subprocess
from unittest.mock import AsyncMock, MagicMock

import pytest

from veridical.api.client import JulesClient
from veridical.api.models import GitPatch, SessionResponse, SessionState
from veridical.models.result import PatchResult, PatchStatus
from veridical.supervisor.loop import Supervisor
from veridical.worker.jules import JulesWorker


def create_session_response(session_id: str, state: SessionState) -> SessionResponse:
    """Helper to create a SessionResponse."""
    return SessionResponse(
        name=f"sessions/{session_id}",
        state=state,
        createTime="2024-01-01T00:00:00Z",
        updateTime="2024-01-01T00:00:00Z",
    )


def create_patch_content(file_path: str, old_line: str, new_line: str) -> str:
    """Helper to create a valid unified diff patch."""
    return f"""diff --git a/{file_path} b/{file_path}
index 1234567..abcdefg 100644
--- a/{file_path}
+++ b/{file_path}
@@ -1 +1 @@
-{old_line}
+{new_line}
"""


@pytest.mark.e2e
class TestJulesSupervisorE2E:
    """End-to-end tests for Jules Supervisor."""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self, e2e_temp_repo, e2e_config):
        """Test flow when verification passes on the first try."""
        session_id = "test-session-first-try"
        mock_client = AsyncMock(spec=JulesClient)
        mock_client.create_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.IN_PROGRESS)
        )
        mock_client.get_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.COMPLETED)
        )
        mock_client.download_patch = AsyncMock(
            return_value=GitPatch(
                unidiff_patch=create_patch_content(
                    "README.md", "# Test Project", "# Success first try"
                )
            )
        )

        worker = JulesWorker(e2e_config, mock_client, e2e_temp_repo)
        supervisor = Supervisor(e2e_config, worker, e2e_temp_repo)
        supervisor.verifier.run_all = AsyncMock(return_value=MagicMock(passed=True))

        result = await supervisor.run("Simple task")
        assert result.success is True
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_full_flow_with_retry(self, e2e_temp_repo, e2e_config):
        """Test the complete flow: create session → fail verification → retry → succeed."""
        session_id = "test-session-retry"
        mock_client = AsyncMock(spec=JulesClient)
        mock_client.create_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.IN_PROGRESS)
        )
        mock_client.get_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.COMPLETED)
        )
        mock_client.send_message = AsyncMock()

        # Returns different patches
        mock_client.download_patch = AsyncMock(
            side_effect=[
                GitPatch(
                    unidiff_patch=create_patch_content("README.md", "# Test Project", "# Try 1")
                ),
                GitPatch(
                    unidiff_patch=create_patch_content("README.md", "# Test Project", "# Try 2")
                ),
            ]
        )

        worker = JulesWorker(e2e_config, mock_client, e2e_temp_repo)
        supervisor = Supervisor(e2e_config, worker, e2e_temp_repo)

        # Mock verifier: fail then pass
        supervisor.verifier.run_all = AsyncMock(
            side_effect=[MagicMock(passed=False), MagicMock(passed=True)]
        )
        supervisor.verifier.generate_feedback = AsyncMock(return_value="Fail")

        result = await supervisor.run("Retry task")
        assert result.success is True
        assert result.iterations == 2
        assert mock_client.send_message.called

    @pytest.mark.asyncio
    async def test_max_iterations_exceeded(self, e2e_temp_repo, e2e_config):
        """Test that supervisor stops after max iterations."""
        e2e_config.supervisor.max_iterations = 2
        session_id = "test-max-iter"
        mock_client = AsyncMock(spec=JulesClient)
        mock_client.create_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.IN_PROGRESS)
        )
        mock_client.get_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.COMPLETED)
        )
        mock_client.download_patch = AsyncMock(
            return_value=GitPatch(
                unidiff_patch=create_patch_content("README.md", "# Test Project", "# Fail")
            )
        )

        worker = JulesWorker(e2e_config, mock_client, e2e_temp_repo)
        supervisor = Supervisor(e2e_config, worker, e2e_temp_repo)
        supervisor.verifier.run_all = AsyncMock(return_value=MagicMock(passed=False))
        supervisor.verifier.generate_feedback = AsyncMock(return_value="Fail")

        result = await supervisor.run("Always failing")
        assert result.success is False
        assert result.iterations == 3
        assert "Maximum iterations exceeded" in result.failure_reason

    @pytest.mark.asyncio
    async def test_resume_existing_session_id(self, e2e_temp_repo, e2e_config):
        """Test resuming an existing session with --session-id."""
        session_id = "existing-sess-123"
        mock_client = AsyncMock(spec=JulesClient)
        mock_client.get_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.COMPLETED)
        )
        mock_client.download_patch = AsyncMock(return_value=GitPatch(unidiff_patch=""))

        worker = JulesWorker(e2e_config, mock_client, e2e_temp_repo)
        supervisor = Supervisor(e2e_config, worker, e2e_temp_repo)
        supervisor.verifier.run_all = AsyncMock(return_value=MagicMock(passed=True))

        result = await supervisor.run("Resume", session_id=session_id)
        assert result.success is True
        mock_client.create_session.assert_not_called()
        mock_client.get_session.assert_called_with(session_id)

    @pytest.mark.asyncio
    async def test_stagnation_detection(self, e2e_temp_repo, e2e_config):
        """Test that identical patches trip the stagnation detection circuit breaker (Task 2.7)."""
        e2e_config.supervisor.stagnation_threshold = 2
        session_id = "test-stagnation"
        mock_client = AsyncMock(spec=JulesClient)
        mock_client.create_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.IN_PROGRESS)
        )
        mock_client.get_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.COMPLETED)
        )

        worker = JulesWorker(e2e_config, mock_client, e2e_temp_repo)
        supervisor = Supervisor(e2e_config, worker, e2e_temp_repo)

        worker.synchronizer.apply_session_patch = AsyncMock(
            return_value=(
                "branch",
                PatchResult(
                    success=True,
                    files_changed=["README.md"],
                    diff_hash="identical-hash",
                    status=PatchStatus.APPLIED,
                ),
            )
        )

        supervisor.verifier.run_all = AsyncMock(return_value=MagicMock(passed=False))
        supervisor.verifier.generate_feedback = AsyncMock(return_value="Fail")

        result = await supervisor.run("Stagnate")
        assert result.success is False
        assert "Stagnation detected" in result.failure_reason
        assert result.iterations == 2

    @pytest.mark.asyncio
    async def test_patch_application_failure(self, e2e_temp_repo, e2e_config):
        """Test that patch application failure returns FAILED result immediately (Task 2.8)."""
        session_id = "test-patch-fail"
        mock_client = AsyncMock(spec=JulesClient)
        mock_client.create_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.IN_PROGRESS)
        )
        mock_client.get_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.COMPLETED)
        )

        worker = JulesWorker(e2e_config, mock_client, e2e_temp_repo)
        supervisor = Supervisor(e2e_config, worker, e2e_temp_repo)

        worker.synchronizer.apply_session_patch = AsyncMock(
            return_value=(
                None,
                PatchResult(
                    success=False, error="Failed to apply patch", status=PatchStatus.FAILED
                ),
            )
        )

        result = await supervisor.run("Failing patch")
        assert result.success is False
        assert result.failure_reason == "Patch failed to apply"

    @pytest.mark.asyncio
    async def test_api_polling_error(self, e2e_temp_repo, e2e_config):
        """Test that API error during polling returns FAILED result (Task 2.9)."""
        e2e_config.supervisor.max_consecutive_failures = 1
        session_id = "test-api-error"
        mock_client = AsyncMock(spec=JulesClient)
        mock_client.create_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.IN_PROGRESS)
        )
        mock_client.get_session = AsyncMock(side_effect=Exception("API Down"))

        worker = JulesWorker(e2e_config, mock_client, e2e_temp_repo)
        supervisor = Supervisor(e2e_config, worker, e2e_temp_repo)

        result = await supervisor.run("API error")
        assert result.success is False
        assert "Maximum consecutive failures reached" in result.failure_reason

    @pytest.mark.asyncio
    async def test_state_file_cleanup(self, e2e_temp_repo, e2e_config):
        """Test that .veridical_state.json is cleaned up after success (Task 2.10)."""
        session_id = "test-cleanup"
        state_file = e2e_temp_repo / ".veridical_state.json"
        mock_client = AsyncMock(spec=JulesClient)
        mock_client.create_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.IN_PROGRESS)
        )
        mock_client.get_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.COMPLETED)
        )
        mock_client.download_patch = AsyncMock(return_value=GitPatch(unidiff_patch=""))

        worker = JulesWorker(e2e_config, mock_client, e2e_temp_repo)
        supervisor = Supervisor(e2e_config, worker, e2e_temp_repo)
        worker.synchronizer.merge_to_main = MagicMock(return_value="hash123")
        worker.synchronizer.apply_session_patch = AsyncMock(
            return_value=("branch", PatchResult(success=True, status=PatchStatus.APPLIED))
        )
        supervisor.verifier.run_all = AsyncMock(return_value=MagicMock(passed=True))

        result = await supervisor.run("Clean task")
        assert result.success is True
        assert not state_file.exists()

    @pytest.mark.asyncio
    async def test_branch_state_during_flow(self, e2e_temp_repo, e2e_config):
        """Test that branch state is correct at each step of the flow (Task 2.6)."""
        session_id = "test-branch-state"
        branch_states = []
        mock_client = AsyncMock(spec=JulesClient)
        mock_client.create_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.IN_PROGRESS)
        )
        mock_client.get_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.COMPLETED)
        )
        worker = JulesWorker(e2e_config, mock_client, e2e_temp_repo)
        supervisor = Supervisor(e2e_config, worker, e2e_temp_repo)

        async def mock_apply_session_patch(_client, _session_id, _iteration):
            branch_name = f"veridical/iter-{_iteration}"
            worker.synchronizer.create_iteration_branch(_iteration)
            res = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=e2e_temp_repo,
                capture_output=True,
                text=True,
            )
            branch_states.append(("patch", res.stdout.strip()))
            return branch_name, PatchResult(
                success=True,
                files_changed=[],
                diff_hash=f"h{_iteration}",
                status=PatchStatus.APPLIED,
            )

        worker.synchronizer.apply_session_patch = mock_apply_session_patch

        async def mock_verify():
            res = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=e2e_temp_repo,
                capture_output=True,
                text=True,
            )
            branch_states.append(("verify", res.stdout.strip()))
            return MagicMock(passed=True)

        supervisor.verifier.run_all = mock_verify
        worker.synchronizer.merge_to_main = MagicMock(return_value="hash123")
        await supervisor.run("Branch state test")
        for _phase, branch in branch_states:
            assert branch.startswith("veridical/")
