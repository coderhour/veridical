"""Conflict resolver - sequential merge of subtask branches."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from veridical.local.gtr import GtrWorktreeManager

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MergeOutcome:
    """Outcome of merging a single branch."""

    branch: str
    success: bool
    error: str | None = None


@dataclass
class MergeResult:
    """Aggregated result of sequential branch merges."""

    outcomes: list[MergeOutcome] = field(default_factory=list)

    @property
    def all_merged(self) -> bool:
        return all(o.success for o in self.outcomes)

    @property
    def merged_branches(self) -> list[str]:
        return [o.branch for o in self.outcomes if o.success]

    @property
    def conflicted_branches(self) -> list[str]:
        return [o.branch for o in self.outcomes if not o.success]


class ConflictResolver:
    """Merge subtask branches sequentially with conflict detection.

    Branches are merged one at a time into the target branch so that
    conflicts are detected incrementally.  In v1, conflicts are reported
    for human resolution rather than auto-resolved.
    """

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self._gtr = GtrWorktreeManager(repo_path)

    def merge_branches(
        self,
        branches: list[str],
        target_branch: str,
    ) -> MergeResult:
        """Merge *branches* sequentially into *target_branch*.

        Each branch is merged one at a time.  If a merge fails the
        merge is aborted and the branch is recorded as conflicted.
        Subsequent branches are still attempted.

        Args:
            branches: Ordered list of branch names to merge.
            target_branch: Branch to merge into.

        Returns:
            :class:`MergeResult` with per-branch outcomes.
        """
        result = MergeResult()

        for branch in branches:
            logger.info("Merging branch %s into %s", branch, target_branch)
            merged = self._gtr.merge_worktree_branch(branch, target_branch)

            if merged:
                logger.info("Successfully merged %s", branch)
                result.outcomes.append(MergeOutcome(branch=branch, success=True))
            else:
                error_msg = (
                    f"Merge conflict: could not auto-merge {branch} "
                    f"into {target_branch}. Worktree preserved for manual resolution."
                )
                logger.warning(error_msg)
                result.outcomes.append(MergeOutcome(branch=branch, success=False, error=error_msg))

        return result

    def cleanup_branches(
        self,
        branches: list[str],
        *,
        auto_cleanup: bool = True,
    ) -> None:
        """Remove worktrees for successfully merged branches.

        Args:
            branches: Branch names to clean up.
            auto_cleanup: If False, skip cleanup (preserve worktrees).
        """
        if not auto_cleanup:
            logger.info("Skipping worktree cleanup (auto_cleanup=false)")
            return

        for branch in branches:
            try:
                self._gtr.remove_worktree(branch)
                logger.info("Cleaned up worktree for %s", branch)
            except RuntimeError as e:
                logger.warning("Failed to clean up worktree %s: %s", branch, e)
