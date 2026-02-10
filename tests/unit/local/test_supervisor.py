from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from veridical.config.schema import (
    LocalConfig,
    SupervisorConfig,
    VeridicalConfig,
    VerifierConfig,
    WorkLogConfig,
)
from veridical.local.supervisor import LocalSupervisor
from veridical.models.result import VerificationResult


@pytest.fixture
def config():
    return VeridicalConfig(
        local=LocalConfig(
            worker_command="echo hello",
            worker_timeout=10,
            mode="subprocess",
        ),
        supervisor=SupervisorConfig(
            max_iterations=5,
            max_consecutive_failures=3,
        ),
        verifier=VerifierConfig(quality_gates=[]),
        worklog=WorkLogConfig(enabled=False),
    )


@pytest.fixture
def console():
    return MagicMock(spec=Console)


@pytest.fixture
def repo_path(tmp_path):
    return tmp_path


@pytest.mark.asyncio
async def test_supervisor_run_success(config, console, repo_path):
    supervisor = LocalSupervisor(config, repo_path, console=console)

    # Mock runner
    supervisor.runner.run = AsyncMock(return_value=0)

    # Mock verifier
    supervisor.verifier.run_all = AsyncMock(
        return_value=VerificationResult(
            passed=True, gates=[], duration_seconds=1.0, timestamp=datetime.now()
        )
    )

    result = await supervisor.run("Fix bug")

    assert result.success is True
    assert result.iterations == 1
    supervisor.runner.run.assert_called_once()
    supervisor.verifier.run_all.assert_called_once()


@pytest.mark.asyncio
async def test_supervisor_retry_loop(config, console, repo_path):
    supervisor = LocalSupervisor(config, repo_path, console=console)

    # Mock runner
    supervisor.runner.run = AsyncMock(return_value=0)

    # Mock verifier
    # First run fails, second run passes
    fail_result = VerificationResult(
        passed=False, gates=[], duration_seconds=1.0, timestamp=datetime.now()
    )
    pass_result = VerificationResult(
        passed=True, gates=[], duration_seconds=1.0, timestamp=datetime.now()
    )
    supervisor.verifier.run_all = AsyncMock(side_effect=[fail_result, pass_result])
    supervisor.verifier.generate_feedback = AsyncMock(return_value="Error context")

    result = await supervisor.run("Fix bug")

    assert result.success is True
    assert result.iterations == 2
    assert supervisor.runner.run.call_count == 2

    # Check that error context was passed to second run
    supervisor.runner.run.assert_called_with("Error context", task="Fix bug")


@pytest.mark.asyncio
async def test_supervisor_max_iterations(config, console, repo_path):
    config.supervisor.max_iterations = 2
    supervisor = LocalSupervisor(config, repo_path, console=console)

    supervisor.runner.run = AsyncMock(return_value=0)
    fail_result = VerificationResult(
        passed=False, gates=[], duration_seconds=1.0, timestamp=datetime.now()
    )
    supervisor.verifier.run_all = AsyncMock(return_value=fail_result)
    supervisor.verifier.generate_feedback = AsyncMock(return_value="Error context")

    result = await supervisor.run("Fix bug")

    assert result.success is False
    assert result.iterations == 2
    assert result.failure_reason == "Maximum iterations exceeded"


# ---------------------------------------------------------------------------
# gtr worktree integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_supervisor_with_gtr_creates_worktree(config, console, repo_path):
    """When gtr_branch is set, supervisor creates a worktree before the loop."""
    with patch("veridical.local.supervisor.GtrWorktreeManager") as MockManager:
        mock_mgr = MagicMock()
        mock_mgr.create_worktree.return_value = Path("/tmp/worktree")
        mock_mgr.merge_worktree_branch.return_value = True
        mock_mgr.remove_worktree.return_value = None
        MockManager.return_value = mock_mgr

        supervisor = LocalSupervisor(
            config, repo_path, console=console, gtr_branch="veri/my-feature"
        )
        supervisor.runner.run = AsyncMock(return_value=0)
        supervisor.verifier.run_all = AsyncMock(
            return_value=VerificationResult(
                passed=True, gates=[], duration_seconds=1.0, timestamp=datetime.now()
            )
        )

        with patch.object(supervisor, "_get_starting_branch", return_value="main"):
            result = await supervisor.run("Fix bug")

        assert result.success is True
        mock_mgr.create_worktree.assert_called_once_with("veri/my-feature")


@pytest.mark.asyncio
async def test_supervisor_with_gtr_merges_on_success(config, console, repo_path):
    """On success, supervisor merges worktree branch and cleans up."""
    with patch("veridical.local.supervisor.GtrWorktreeManager") as MockManager:
        mock_mgr = MagicMock()
        mock_mgr.create_worktree.return_value = Path("/tmp/worktree")
        mock_mgr.merge_worktree_branch.return_value = True
        mock_mgr.remove_worktree.return_value = None
        MockManager.return_value = mock_mgr

        supervisor = LocalSupervisor(
            config, repo_path, console=console, gtr_branch="veri/my-feature"
        )
        supervisor.runner.run = AsyncMock(return_value=0)
        supervisor.verifier.run_all = AsyncMock(
            return_value=VerificationResult(
                passed=True, gates=[], duration_seconds=1.0, timestamp=datetime.now()
            )
        )

        with patch.object(supervisor, "_get_starting_branch", return_value="main"):
            result = await supervisor.run("Fix bug")

        assert result.success is True
        mock_mgr.merge_worktree_branch.assert_called_once_with("veri/my-feature", "main")
        mock_mgr.remove_worktree.assert_called_once_with("veri/my-feature")


@pytest.mark.asyncio
async def test_supervisor_with_gtr_no_cleanup_when_disabled(config, console, repo_path):
    """When gtr_auto_cleanup is false, worktree is kept after merge."""
    config.local.gtr_auto_cleanup = False

    with patch("veridical.local.supervisor.GtrWorktreeManager") as MockManager:
        mock_mgr = MagicMock()
        mock_mgr.create_worktree.return_value = Path("/tmp/worktree")
        mock_mgr.merge_worktree_branch.return_value = True
        MockManager.return_value = mock_mgr

        supervisor = LocalSupervisor(
            config, repo_path, console=console, gtr_branch="veri/my-feature"
        )
        supervisor.runner.run = AsyncMock(return_value=0)
        supervisor.verifier.run_all = AsyncMock(
            return_value=VerificationResult(
                passed=True, gates=[], duration_seconds=1.0, timestamp=datetime.now()
            )
        )

        with patch.object(supervisor, "_get_starting_branch", return_value="main"):
            result = await supervisor.run("Fix bug")

        assert result.success is True
        mock_mgr.merge_worktree_branch.assert_called_once()
        mock_mgr.remove_worktree.assert_not_called()


@pytest.mark.asyncio
async def test_supervisor_with_gtr_merge_conflict(config, console, repo_path):
    """On merge conflict, worktree is preserved and user is instructed."""
    with patch("veridical.local.supervisor.GtrWorktreeManager") as MockManager:
        mock_mgr = MagicMock()
        mock_mgr.create_worktree.return_value = Path("/tmp/worktree")
        mock_mgr.merge_worktree_branch.return_value = False  # conflict
        MockManager.return_value = mock_mgr

        supervisor = LocalSupervisor(
            config, repo_path, console=console, gtr_branch="veri/my-feature"
        )
        supervisor.runner.run = AsyncMock(return_value=0)
        supervisor.verifier.run_all = AsyncMock(
            return_value=VerificationResult(
                passed=True, gates=[], duration_seconds=1.0, timestamp=datetime.now()
            )
        )

        with patch.object(supervisor, "_get_starting_branch", return_value="main"):
            result = await supervisor.run("Fix bug")

        assert result.success is True
        mock_mgr.remove_worktree.assert_not_called()
        # Check that merge conflict message was printed
        printed = " ".join(str(c) for c in console.print.call_args_list)
        assert "Merge conflict" in printed or "merge" in printed.lower()


@pytest.mark.asyncio
async def test_supervisor_with_gtr_failure_preserves_worktree(config, console, repo_path):
    """On loop failure, worktree is preserved for inspection."""
    config.supervisor.max_iterations = 1

    fail_result = VerificationResult(
        passed=False, gates=[], duration_seconds=1.0, timestamp=datetime.now()
    )

    with (
        patch("veridical.local.supervisor.GtrWorktreeManager") as MockManager,
        patch("veridical.local.supervisor.Verifier") as MockVerifier,
    ):
        mock_mgr = MagicMock()
        mock_mgr.create_worktree.return_value = Path("/tmp/worktree")
        MockManager.return_value = mock_mgr

        mock_verifier = MagicMock()
        mock_verifier.run_all = AsyncMock(return_value=fail_result)
        mock_verifier.generate_feedback = AsyncMock(return_value="Error")
        MockVerifier.return_value = mock_verifier

        supervisor = LocalSupervisor(
            config, repo_path, console=console, gtr_branch="veri/my-feature"
        )
        supervisor.runner.run = AsyncMock(return_value=0)

        result = await supervisor.run("Fix bug")

        assert result.success is False
        mock_mgr.merge_worktree_branch.assert_not_called()
        mock_mgr.remove_worktree.assert_not_called()
        # Check preserved message
        printed = " ".join(str(c) for c in console.print.call_args_list)
        assert "preserved" in printed.lower() or "worktree" in printed.lower()


@pytest.mark.asyncio
async def test_supervisor_without_gtr_unchanged(config, console, repo_path):
    """Without gtr_branch, supervisor behaves exactly as before."""
    supervisor = LocalSupervisor(config, repo_path, console=console)

    assert supervisor.gtr_branch is None
    assert supervisor._gtr_manager is None

    supervisor.runner.run = AsyncMock(return_value=0)
    supervisor.verifier.run_all = AsyncMock(
        return_value=VerificationResult(
            passed=True, gates=[], duration_seconds=1.0, timestamp=datetime.now()
        )
    )

    result = await supervisor.run("Fix bug")
    assert result.success is True
