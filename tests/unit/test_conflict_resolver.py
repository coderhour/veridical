"""Unit tests for ConflictResolver."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from veridical.orchestrator.resolver import ConflictResolver, MergeOutcome, MergeResult


@pytest.fixture
def resolver(tmp_path: Path) -> ConflictResolver:
    return ConflictResolver(tmp_path)


class TestMergeResult:
    def test_all_merged(self) -> None:
        result = MergeResult(
            outcomes=[
                MergeOutcome(branch="b1", success=True),
                MergeOutcome(branch="b2", success=True),
            ]
        )
        assert result.all_merged is True
        assert result.merged_branches == ["b1", "b2"]
        assert result.conflicted_branches == []

    def test_some_conflicts(self) -> None:
        result = MergeResult(
            outcomes=[
                MergeOutcome(branch="b1", success=True),
                MergeOutcome(branch="b2", success=False, error="conflict"),
            ]
        )
        assert result.all_merged is False
        assert result.merged_branches == ["b1"]
        assert result.conflicted_branches == ["b2"]

    def test_empty(self) -> None:
        result = MergeResult()
        assert result.all_merged is True
        assert result.merged_branches == []


class TestMergeBranches:
    @patch("veridical.orchestrator.resolver.GtrWorktreeManager")
    def test_all_succeed(self, mock_gtr_cls: MagicMock, tmp_path: Path) -> None:
        mock_gtr = MagicMock()
        mock_gtr.merge_worktree_branch.return_value = True
        mock_gtr_cls.return_value = mock_gtr

        resolver = ConflictResolver(tmp_path)
        resolver._gtr = mock_gtr

        result = resolver.merge_branches(["b1", "b2"], "main")
        assert result.all_merged is True
        assert len(result.outcomes) == 2
        assert mock_gtr.merge_worktree_branch.call_count == 2

    @patch("veridical.orchestrator.resolver.GtrWorktreeManager")
    def test_conflict_detected(self, mock_gtr_cls: MagicMock, tmp_path: Path) -> None:
        mock_gtr = MagicMock()
        mock_gtr.merge_worktree_branch.side_effect = [True, False]
        mock_gtr_cls.return_value = mock_gtr

        resolver = ConflictResolver(tmp_path)
        resolver._gtr = mock_gtr

        result = resolver.merge_branches(["b1", "b2"], "main")
        assert result.all_merged is False
        assert result.merged_branches == ["b1"]
        assert result.conflicted_branches == ["b2"]

    @patch("veridical.orchestrator.resolver.GtrWorktreeManager")
    def test_continues_after_conflict(self, mock_gtr_cls: MagicMock, tmp_path: Path) -> None:
        mock_gtr = MagicMock()
        mock_gtr.merge_worktree_branch.side_effect = [False, True, True]
        mock_gtr_cls.return_value = mock_gtr

        resolver = ConflictResolver(tmp_path)
        resolver._gtr = mock_gtr

        result = resolver.merge_branches(["b1", "b2", "b3"], "main")
        assert len(result.outcomes) == 3
        assert result.conflicted_branches == ["b1"]
        assert result.merged_branches == ["b2", "b3"]


class TestCleanupBranches:
    @patch("veridical.orchestrator.resolver.GtrWorktreeManager")
    def test_cleanup_removes_worktrees(self, mock_gtr_cls: MagicMock, tmp_path: Path) -> None:
        mock_gtr = MagicMock()
        mock_gtr_cls.return_value = mock_gtr

        resolver = ConflictResolver(tmp_path)
        resolver._gtr = mock_gtr

        resolver.cleanup_branches(["b1", "b2"], auto_cleanup=True)
        assert mock_gtr.remove_worktree.call_count == 2

    @patch("veridical.orchestrator.resolver.GtrWorktreeManager")
    def test_cleanup_skipped_when_disabled(self, mock_gtr_cls: MagicMock, tmp_path: Path) -> None:
        mock_gtr = MagicMock()
        mock_gtr_cls.return_value = mock_gtr

        resolver = ConflictResolver(tmp_path)
        resolver._gtr = mock_gtr

        resolver.cleanup_branches(["b1"], auto_cleanup=False)
        mock_gtr.remove_worktree.assert_not_called()

    @patch("veridical.orchestrator.resolver.GtrWorktreeManager")
    def test_cleanup_handles_failure(self, mock_gtr_cls: MagicMock, tmp_path: Path) -> None:
        mock_gtr = MagicMock()
        mock_gtr.remove_worktree.side_effect = RuntimeError("cleanup failed")
        mock_gtr_cls.return_value = mock_gtr

        resolver = ConflictResolver(tmp_path)
        resolver._gtr = mock_gtr

        # Should not raise
        resolver.cleanup_branches(["b1"], auto_cleanup=True)
