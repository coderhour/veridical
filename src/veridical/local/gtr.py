"""gtr (Git Worktree Runner) integration for Veridical local loop."""

import logging
import shutil
import subprocess
from pathlib import Path

from veridical.synchronizer.branch import sanitize_branch_name

logger = logging.getLogger(__name__)

GTR_BRANCH_PREFIX = "veri/"
GTR_INSTALL_URL = "https://github.com/coderabbitai/git-worktree-runner"


def detect_gtr() -> bool:
    """Check if gtr is available on PATH.

    Returns:
        True if ``git-gtr`` binary is found on PATH.
    """
    return shutil.which("git-gtr") is not None


def generate_gtr_branch_name(
    spec_name: str | None,
    task_description: str,
) -> str:
    """Generate a branch name for a gtr worktree.

    Uses the spec name when available, otherwise falls back to the task
    description.  The result is prefixed with ``veri/`` to namespace
    worktree branches.

    Args:
        spec_name: Optional OpenSpec change name (e.g. ``"add-user-auth"``).
        task_description: Free-text task description used as fallback.

    Returns:
        Branch name like ``veri/add-user-auth``.
    """
    raw = spec_name or task_description
    sanitized = sanitize_branch_name(raw)
    return f"{GTR_BRANCH_PREFIX}{sanitized}"


class GtrWorktreeManager:
    """Thin wrapper around the ``git gtr`` CLI for worktree lifecycle.

    All heavy lifting is delegated to the external ``gtr`` tool.
    """

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path

    # ------------------------------------------------------------------
    # Worktree lifecycle
    # ------------------------------------------------------------------

    def create_worktree(self, branch_name: str) -> Path:
        """Create a new worktree via ``git gtr new``.

        Args:
            branch_name: Branch name (e.g. ``veri/add-user-auth``).

        Returns:
            Absolute path to the created worktree directory.

        Raises:
            RuntimeError: If the gtr command fails.
        """
        logger.info(f"Creating gtr worktree for branch: {branch_name}")
        result = subprocess.run(
            ["git", "gtr", "new", branch_name, "--no-hooks", "--yes"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"git gtr new failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        return self.get_worktree_path(branch_name)

    def remove_worktree(self, branch_name: str) -> None:
        """Remove a worktree via ``git gtr rm``.

        Args:
            branch_name: Branch name of the worktree to remove.

        Raises:
            RuntimeError: If the gtr command fails.
        """
        logger.info(f"Removing gtr worktree for branch: {branch_name}")
        result = subprocess.run(
            ["git", "gtr", "rm", branch_name, "--yes"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"git gtr rm failed (exit {result.returncode}): {result.stderr.strip()}"
            )

    def get_worktree_path(self, branch_name: str) -> Path:
        """Get the filesystem path for a worktree via ``git gtr go``.

        Args:
            branch_name: Branch name of the worktree.

        Returns:
            Absolute path to the worktree directory.

        Raises:
            RuntimeError: If the gtr command fails.
        """
        result = subprocess.run(
            ["git", "gtr", "go", branch_name],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"git gtr go failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        return Path(result.stdout.strip())

    def merge_worktree_branch(
        self,
        branch_name: str,
        target_branch: str,
    ) -> bool:
        """Merge the worktree branch into the target branch.

        Performs the merge in the main repo directory.  If the merge
        fails (e.g. conflicts), it is aborted automatically.

        Args:
            branch_name: Worktree branch to merge from.
            target_branch: Branch to merge into.

        Returns:
            True if the merge succeeded, False if it failed (conflicts).
        """
        logger.info(f"Merging {branch_name} into {target_branch}")

        # Checkout target branch
        checkout = subprocess.run(
            ["git", "checkout", target_branch],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if checkout.returncode != 0:
            logger.error(f"Failed to checkout {target_branch}: {checkout.stderr.strip()}")
            return False

        # Attempt merge
        merge = subprocess.run(
            ["git", "merge", branch_name, "--no-edit"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if merge.returncode != 0:
            logger.warning(f"Merge failed, aborting: {merge.stderr.strip()}")
            subprocess.run(
                ["git", "merge", "--abort"],
                cwd=self.repo_path,
                capture_output=True,
                check=False,
            )
            return False

        logger.info(f"Successfully merged {branch_name} into {target_branch}")
        return True
