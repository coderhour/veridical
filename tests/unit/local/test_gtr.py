"""Unit tests for gtr detection, branch name generation, and GtrWorktreeManager."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from veridical.local.gtr import (
    GtrWorktreeManager,
    detect_gtr,
    generate_gtr_branch_name,
)

# ---------------------------------------------------------------------------
# detect_gtr
# ---------------------------------------------------------------------------


class TestDetectGtr:
    @patch("shutil.which", return_value="/usr/local/bin/git-gtr")
    def test_detected(self, mock_which: MagicMock) -> None:
        assert detect_gtr() is True
        mock_which.assert_called_with("git-gtr")

    @patch("shutil.which", return_value=None)
    def test_not_detected(self, _mock_which: MagicMock) -> None:
        assert detect_gtr() is False


# ---------------------------------------------------------------------------
# generate_gtr_branch_name
# ---------------------------------------------------------------------------


class TestGenerateGtrBranchName:
    def test_from_spec_name(self) -> None:
        result = generate_gtr_branch_name("add-user-auth", "some task")
        assert result == "veri/add-user-auth"

    def test_from_task_description(self) -> None:
        result = generate_gtr_branch_name(None, "Fix login validation bug")
        assert result == "veri/fix-login-validation-bug"

    def test_sanitizes_special_chars(self) -> None:
        result = generate_gtr_branch_name("Add User's Auth (v2.0)", "fallback")
        assert result == "veri/add-users-auth-v20"

    def test_sanitizes_underscores(self) -> None:
        result = generate_gtr_branch_name(None, "Fix_login bug")
        assert result == "veri/fix-login-bug"

    def test_empty_spec_name_uses_task(self) -> None:
        result = generate_gtr_branch_name("", "My task")
        # Empty string is falsy, so task_description is used
        assert result == "veri/my-task"

    def test_fallback_on_empty(self) -> None:
        result = generate_gtr_branch_name(None, "!!!")
        assert result == "veri/veridical-work"


# ---------------------------------------------------------------------------
# GtrWorktreeManager
# ---------------------------------------------------------------------------


class TestGtrWorktreeManager:
    @pytest.fixture
    def manager(self, tmp_path: Path) -> GtrWorktreeManager:
        return GtrWorktreeManager(tmp_path)

    @patch("subprocess.run")
    def test_create_worktree_success(
        self, mock_run: MagicMock, manager: GtrWorktreeManager
    ) -> None:
        # First call: git gtr new
        new_result = MagicMock(returncode=0, stdout="", stderr="")
        # Second call: git gtr go (from get_worktree_path)
        go_result = MagicMock(returncode=0, stdout="/tmp/worktree\n", stderr="")
        mock_run.side_effect = [new_result, go_result]

        path = manager.create_worktree("veri/my-feature")

        assert path == Path("/tmp/worktree")
        assert mock_run.call_count == 2
        new_call = mock_run.call_args_list[0]
        assert new_call.args[0] == ["git", "gtr", "new", "veri/my-feature", "--no-hooks", "--yes"]

    @patch("subprocess.run")
    def test_create_worktree_failure(
        self, mock_run: MagicMock, manager: GtrWorktreeManager
    ) -> None:
        mock_run.return_value = MagicMock(returncode=1, stderr="branch exists")
        with pytest.raises(RuntimeError, match="git gtr new failed"):
            manager.create_worktree("veri/my-feature")

    @patch("subprocess.run")
    def test_remove_worktree_success(
        self, mock_run: MagicMock, manager: GtrWorktreeManager
    ) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        manager.remove_worktree("veri/my-feature")
        mock_run.assert_called_once()
        assert mock_run.call_args.args[0] == ["git", "gtr", "rm", "veri/my-feature", "--yes"]

    @patch("subprocess.run")
    def test_remove_worktree_failure(
        self, mock_run: MagicMock, manager: GtrWorktreeManager
    ) -> None:
        mock_run.return_value = MagicMock(returncode=1, stderr="not found")
        with pytest.raises(RuntimeError, match="git gtr rm failed"):
            manager.remove_worktree("veri/my-feature")

    @patch("subprocess.run")
    def test_get_worktree_path(self, mock_run: MagicMock, manager: GtrWorktreeManager) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="/home/user/repo-my-feature\n", stderr=""
        )
        path = manager.get_worktree_path("veri/my-feature")
        assert path == Path("/home/user/repo-my-feature")

    @patch("subprocess.run")
    def test_get_worktree_path_failure(
        self, mock_run: MagicMock, manager: GtrWorktreeManager
    ) -> None:
        mock_run.return_value = MagicMock(returncode=1, stderr="unknown branch")
        with pytest.raises(RuntimeError, match="git gtr go failed"):
            manager.get_worktree_path("veri/nonexistent")

    @patch("subprocess.run")
    def test_merge_worktree_branch_success(
        self, mock_run: MagicMock, manager: GtrWorktreeManager
    ) -> None:
        # checkout succeeds, merge succeeds
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # checkout
            MagicMock(returncode=0, stdout="", stderr=""),  # merge
        ]
        result = manager.merge_worktree_branch("veri/my-feature", "main")
        assert result is True
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_merge_worktree_branch_conflict(
        self, mock_run: MagicMock, manager: GtrWorktreeManager
    ) -> None:
        # checkout succeeds, merge fails, abort called
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # checkout
            MagicMock(returncode=1, stdout="", stderr="CONFLICT"),  # merge
            MagicMock(returncode=0, stdout="", stderr=""),  # merge --abort
        ]
        result = manager.merge_worktree_branch("veri/my-feature", "main")
        assert result is False
        assert mock_run.call_count == 3
        abort_call = mock_run.call_args_list[2]
        assert abort_call.args[0] == ["git", "merge", "--abort"]

    @patch("subprocess.run")
    def test_merge_worktree_branch_checkout_fails(
        self, mock_run: MagicMock, manager: GtrWorktreeManager
    ) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = manager.merge_worktree_branch("veri/my-feature", "main")
        assert result is False
        assert mock_run.call_count == 1
