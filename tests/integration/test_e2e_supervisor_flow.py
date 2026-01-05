"""End-to-end test for the complete Supervisor flow.

This test simulates a full Veridical workflow:
1. User runs `veri run` to start a new feature request
2. Jules session is created
3. Poll states until COMPLETED
4. Create branch, apply patch, run verification
5. Verification fails → generate feedback prompt
6. Send feedback to the same Jules session
7. Cleanup the failed branch
8. Poll states again until COMPLETED
9. Create new branch, apply patch, verify again
10. Verification passes → commit, merge to main, cleanup branch
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from veridical.api.client import JulesClient
from veridical.api.models import SessionResponse, SessionState
from veridical.config.schema import (
    GitConfig,
    JulesConfig,
    QualityGate,
    SupervisorConfig,
    VeridicalConfig,
    VerifierConfig,
)
from veridical.models.result import PatchResult, PatchStatus
from veridical.supervisor.loop import Supervisor


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Add a fake remote origin (required by Dispatcher)
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/test-owner/test-repo.git"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial file and commit
        (repo_path / "README.md").write_text("# Test Project\n")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create main branch if not exists
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
        current_branch = result.stdout.strip()
        if current_branch != "main":
            subprocess.run(
                ["git", "branch", "-M", "main"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

        yield repo_path


@pytest.fixture
def test_config(temp_git_repo):  # noqa: ARG001
    """Create a test configuration."""
    return VeridicalConfig(
        jules=JulesConfig(
            api_base_url="https://test.example.com",
            poll_interval=1,  # Fast polling for tests
            poll_timeout=60,
            auto_approve_plans=True,
        ),
        supervisor=SupervisorConfig(
            max_iterations=5,
            max_consecutive_failures=3,
            stagnation_threshold=3,
        ),
        verifier=VerifierConfig(
            quality_gates=[
                # Use a simple command that we can control
                QualityGate(name="test-gate", command="exit 0", timeout=10, required=True),
            ],
        ),
        git=GitConfig(
            base_branch="main",
            branch_prefix="veridical/iter-",
            auto_cleanup=True,
        ),
    )


def create_session_response(session_id: str, state: SessionState) -> SessionResponse:
    """Helper to create a SessionResponse."""
    return SessionResponse(
        name=f"sessions/{session_id}",
        state=state,
        createTime="2024-01-01T00:00:00Z",
        updateTime="2024-01-01T00:00:00Z",
    )


def create_patch_content(file_path: str, old_line: str, new_line: str) -> str:
    """Helper to create a valid unified diff patch.

    Note: The old_line and new_line should NOT include the trailing newline.
    The patch format requires the line content match exactly.
    """
    # Git unified diff format for single-line change
    return f"""diff --git a/{file_path} b/{file_path}
index 1234567..abcdefg 100644
--- a/{file_path}
+++ b/{file_path}
@@ -1 +1 @@
-{old_line}
+{new_line}
"""


class TestE2ESupervisorFlow:
    """End-to-end test for the complete Supervisor workflow."""

    @pytest.mark.asyncio
    async def test_full_flow_with_one_retry(self, temp_git_repo, test_config):
        """Test the complete flow: create session → fail verification → retry → succeed.

        Flow:
        1. Create Jules session
        2. Poll until COMPLETED
        3. Create branch iter-1, apply patch, verify → FAIL
        4. Send feedback to same session
        5. Cleanup iter-1 branch
        6. Poll until COMPLETED again
        7. Create branch iter-2, apply patch, verify → PASS
        8. Commit, merge to main, cleanup iter-2 branch
        """
        session_id = "test-session-123"

        # Track API calls
        api_calls = {
            "create_session": 0,
            "get_session": 0,
            "send_message": 0,
            "download_patch": 0,
            "approve_plan": 0,
        }

        # Create mock client
        mock_client = AsyncMock(spec=JulesClient)

        # Mock create_session - should only be called once
        async def mock_create_session(_request):
            api_calls["create_session"] += 1
            return create_session_response(session_id, SessionState.IN_PROGRESS)

        mock_client.create_session = mock_create_session

        # Mock get_session - returns COMPLETED immediately for simplicity
        get_session_call_count = 0

        async def mock_get_session(sid):
            nonlocal get_session_call_count
            api_calls["get_session"] += 1
            get_session_call_count += 1
            # Return COMPLETED immediately each time
            return create_session_response(sid, SessionState.COMPLETED)

        mock_client.get_session = mock_get_session

        # Mock send_message - should be called for feedback on iteration 2
        async def mock_send_message(sid, message):
            api_calls["send_message"] += 1
            assert sid == session_id, "Feedback should be sent to the same session"
            assert "FAIL" in message or "failed" in message.lower() or len(message) > 0

        mock_client.send_message = mock_send_message

        # Mock download_patch - return different patches for each iteration
        download_patch_count = 0

        async def mock_download_patch(_sid):
            nonlocal download_patch_count
            api_calls["download_patch"] += 1
            download_patch_count += 1

            if download_patch_count == 1:
                # First iteration - create a file that will fail verification
                return create_patch_content("README.md", "# Test Project", "# Updated Project v1")
            else:
                # Second iteration - create a file that will pass verification
                return create_patch_content(
                    "README.md", "# Test Project", "# Updated Project v2 - Fixed"
                )

        mock_client.download_patch = mock_download_patch

        # Mock approve_plan (not expected to be called in this test, but just in case)
        mock_client.approve_plan = AsyncMock()

        # Track verification results - fail first, pass second
        verification_call_count = 0

        async def mock_run_all():
            nonlocal verification_call_count
            verification_call_count += 1

            if verification_call_count == 1:
                # First verification fails
                return MagicMock(
                    passed=False,
                    gate_results=[
                        MagicMock(
                            gate_name="test-gate",
                            passed=False,
                            output="Test failed: expected foo, got bar",
                            duration_seconds=1.0,
                        )
                    ],
                )
            else:
                # Second verification passes
                return MagicMock(
                    passed=True,
                    gate_results=[
                        MagicMock(
                            gate_name="test-gate",
                            passed=True,
                            output="All tests passed",
                            duration_seconds=1.0,
                        )
                    ],
                )

        # Create supervisor
        supervisor = Supervisor(test_config, mock_client, temp_git_repo)

        # Track which iteration we're applying a patch for
        patch_application_count = 0

        # Mock the synchronizer's apply_session_patch to avoid actual git patch application
        # But we still need to create real file changes for the merge to work
        async def mock_apply_session_patch(_client, _session_id):
            nonlocal patch_application_count
            patch_application_count += 1
            # Actually modify a file to simulate patch application
            readme = temp_git_repo / "README.md"
            readme.write_text(f"# Updated Project iteration {patch_application_count}\\n")
            return PatchResult(
                success=True,
                files_changed=["README.md"],
                diff_hash=f"hash{patch_application_count}",
                status=PatchStatus.APPLIED,
            )

        supervisor.synchronizer.apply_session_patch = mock_apply_session_patch

        # Mock the verifier's run_all method
        supervisor.verifier.run_all = mock_run_all

        # Mock generate_feedback to return a simple error message
        supervisor.verifier.generate_feedback = MagicMock(
            return_value="VERIFICATION FAILED:\n- test-gate: Test failed: expected foo, got bar"
        )

        # Run the supervisor loop
        result = await supervisor.run("Implement new feature X")

        # Assertions
        assert result.success is True, f"Expected success but got: {result.failure_reason}"
        assert result.iterations == 2, f"Expected 2 iterations, got {result.iterations}"

        # Verify API call counts
        assert api_calls["create_session"] == 1, "Should only create session once"
        assert api_calls["send_message"] == 1, "Should send feedback once (after first failure)"
        # Note: download_patch not tracked since we mock apply_session_patch directly
        assert api_calls["get_session"] >= 2, "Should poll at least twice"

        # Verify we're back on main branch
        result_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        assert result_branch.stdout.strip() == "main", "Should end on main branch"

        # Verify iteration branches are cleaned up
        result_branches = subprocess.run(
            ["git", "branch", "--list", "veridical/*"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        assert result_branches.stdout.strip() == "", "All iteration branches should be cleaned up"

        # Verify the commit was made
        result_log = subprocess.run(
            ["git", "log", "--oneline", "-3"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        log_output = result_log.stdout.strip()
        assert "Merge veridical/iter-2" in log_output, (
            f"Should have merge commit, got: {log_output}"
        )

    @pytest.mark.asyncio
    async def test_success_on_first_try(self, temp_git_repo, test_config):
        """Test flow when verification passes on the first try."""
        session_id = "test-session-first-try"

        mock_client = AsyncMock(spec=JulesClient)

        # Mock create_session
        async def mock_create_session(_request):
            return create_session_response(session_id, SessionState.IN_PROGRESS)

        mock_client.create_session = mock_create_session

        # Mock get_session - return COMPLETED
        mock_client.get_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.COMPLETED)
        )

        # Mock download_patch
        mock_client.download_patch = AsyncMock(
            return_value=create_patch_content(
                "README.md", "# Test Project", "# Success on first try"
            )
        )

        # Create supervisor
        supervisor = Supervisor(test_config, mock_client, temp_git_repo)

        # Mock verifier to pass immediately
        supervisor.verifier.run_all = AsyncMock(
            return_value=MagicMock(
                passed=True,
                gate_results=[
                    MagicMock(
                        gate_name="test-gate",
                        passed=True,
                        output="All tests passed",
                        duration_seconds=1.0,
                    )
                ],
            )
        )

        # Run the supervisor loop
        result = await supervisor.run("Simple task that works first time")

        # Assertions
        assert result.success is True
        assert result.iterations == 1, "Should complete in 1 iteration"

        # Verify we're on main
        result_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        assert result_branch.stdout.strip() == "main"

        # Verify send_message was NOT called (no retry needed)
        mock_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_max_iterations_exceeded(self, temp_git_repo, test_config):
        """Test that supervisor stops after max iterations."""
        # Set max iterations to 2 for faster test
        test_config.supervisor.max_iterations = 2

        session_id = "test-session-max-iter"

        mock_client = AsyncMock(spec=JulesClient)

        # Mock create_session
        mock_client.create_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.IN_PROGRESS)
        )

        # Mock get_session
        mock_client.get_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.COMPLETED)
        )

        # Mock send_message
        mock_client.send_message = AsyncMock()

        # Mock download_patch
        mock_client.download_patch = AsyncMock(
            return_value=create_patch_content("README.md", "# Test Project", "# Always failing")
        )

        # Create supervisor
        supervisor = Supervisor(test_config, mock_client, temp_git_repo)

        # Mock the synchronizer's apply_session_patch to avoid actual git patch application
        async def mock_apply_session_patch(_client, _session_id):
            return PatchResult(
                success=True,
                files_changed=["README.md"],
                diff_hash="abc123",
                status=PatchStatus.APPLIED,
            )

        supervisor.synchronizer.apply_session_patch = mock_apply_session_patch

        # Mock verifier to always fail
        supervisor.verifier.run_all = AsyncMock(
            return_value=MagicMock(
                passed=False,
                gate_results=[
                    MagicMock(
                        gate_name="test-gate",
                        passed=False,
                        output="Test always fails",
                        duration_seconds=1.0,
                    )
                ],
            )
        )
        supervisor.verifier.generate_feedback = MagicMock(return_value="Always failing")

        # Run the supervisor loop
        result = await supervisor.run("Task that always fails verification")

        # Assertions
        assert result.success is False
        # Circuit breaker trips when iteration_count > max_iterations
        # With max_iterations=2, it trips on iteration 3 (3 > 2)
        assert result.iterations == 3, (
            f"Should stop when exceeding max iterations, got {result.iterations}"
        )
        assert "Maximum iterations exceeded" in (result.failure_reason or "")

        # Verify we're back on main (cleanup happened)
        result_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        assert result_branch.stdout.strip() == "main"

    @pytest.mark.asyncio
    async def test_resume_existing_session(self, temp_git_repo, test_config):
        """Test resuming an existing session with --session-id."""
        session_id = "existing-session-456"

        mock_client = AsyncMock(spec=JulesClient)

        # Mock get_session - session is already COMPLETED
        mock_client.get_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.COMPLETED)
        )

        # Mock download_patch
        mock_client.download_patch = AsyncMock(
            return_value=create_patch_content(
                "README.md", "# Test Project", "# Resumed session fix"
            )
        )

        # Create supervisor
        supervisor = Supervisor(test_config, mock_client, temp_git_repo)

        # Mock verifier to pass
        supervisor.verifier.run_all = AsyncMock(
            return_value=MagicMock(
                passed=True,
                gate_results=[
                    MagicMock(
                        gate_name="test-gate",
                        passed=True,
                        output="All tests passed",
                        duration_seconds=1.0,
                    )
                ],
            )
        )

        # Run with existing session ID
        result = await supervisor.run("Continue the fix", session_id=session_id)

        # Assertions
        assert result.success is True
        assert result.iterations == 1

        # Verify create_session was NOT called (we resumed)
        mock_client.create_session.assert_not_called()

        # Verify we polled the existing session
        mock_client.get_session.assert_called_with(session_id)

    @pytest.mark.asyncio
    async def test_branch_state_during_flow(self, temp_git_repo, test_config):
        """Test that branch state is correct at each step of the flow."""
        session_id = "test-branch-state"
        branch_states = []

        mock_client = AsyncMock(spec=JulesClient)

        # Mock create_session
        mock_client.create_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.IN_PROGRESS)
        )

        # Mock get_session
        mock_client.get_session = AsyncMock(
            return_value=create_session_response(session_id, SessionState.COMPLETED)
        )

        # Mock send_message
        mock_client.send_message = AsyncMock()

        # Create supervisor
        supervisor = Supervisor(test_config, mock_client, temp_git_repo)

        # Mock the synchronizer's apply_session_patch to avoid actual git patch application
        # But still track the branch state by calling the mock during apply
        apply_patch_count = 0

        async def mock_apply_session_patch(_client, _session_id):
            nonlocal apply_patch_count
            apply_patch_count += 1
            # Record branch state when patch is applied
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=temp_git_repo,
                check=True,
                capture_output=True,
                text=True,
            )
            branch_states.append(("during_patch_" + str(apply_patch_count), result.stdout.strip()))
            return PatchResult(
                success=True,
                files_changed=["README.md"],
                diff_hash=f"hash{apply_patch_count}",
                status=PatchStatus.APPLIED,
            )

        supervisor.synchronizer.apply_session_patch = mock_apply_session_patch

        # Track verification count
        verify_count = 0

        async def mock_verify():
            nonlocal verify_count
            verify_count += 1

            # Record branch state during verification
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=temp_git_repo,
                check=True,
                capture_output=True,
                text=True,
            )
            branch_states.append(("during_verify_" + str(verify_count), result.stdout.strip()))

            if verify_count == 1:
                return MagicMock(passed=False, gate_results=[])
            return MagicMock(passed=True, gate_results=[])

        supervisor.verifier.run_all = mock_verify
        supervisor.verifier.generate_feedback = MagicMock(return_value="Failed")

        # Run the supervisor
        result = await supervisor.run("Test branch states")

        # Verify branch states
        assert result.success is True

        # Check that we were on iteration branches during verification
        for state_name, branch in branch_states:
            if "verify" in state_name:
                assert branch.startswith("veridical/iter-"), (
                    f"Expected iteration branch during {state_name}, got {branch}"
                )

        # Final state should be on main
        result_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        assert result_branch.stdout.strip() == "main"
