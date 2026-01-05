"""Branch management for the synchronizer."""

import logging
from pathlib import Path

from veridical.synchronizer.git import GitWrapper

logger = logging.getLogger(__name__)


class BranchManager:
    """Manages iteration branches for Veridical.

    Creates and manages isolation branches for each iteration,
    ensuring clean separation of changes.
    """

    def __init__(
        self,
        repo_path: Path,
        *,
        base_branch: str = "main",
        branch_prefix: str = "veridical/iter-",
    ) -> None:
        """Initialize the branch manager.

        Args:
            repo_path: Path to the repository root
            base_branch: Base branch to create iterations from
            branch_prefix: Prefix for iteration branch names
        """
        self.git = GitWrapper(repo_path)
        self.base_branch = base_branch
        self.branch_prefix = branch_prefix

    def get_iteration_branch_name(self, iteration: int) -> str:
        """Get the branch name for an iteration.

        Args:
            iteration: Iteration number

        Returns:
            Branch name
        """
        return f"{self.branch_prefix}{iteration}"

    def create_iteration_branch(self, iteration: int) -> str:
        """Create and checkout an iteration branch.

        If the branch already exists, it will be deleted and recreated.

        Args:
            iteration: Iteration number

        Returns:
            Name of the created branch
        """
        branch_name = self.get_iteration_branch_name(iteration)
        logger.info(f"Creating iteration branch: {branch_name}")

        # Ensure we're on base branch
        logger.debug(f"Checking out base branch: {self.base_branch}")
        self.git.checkout(self.base_branch)

        # Delete if exists
        if self.git.branch_exists(branch_name):
            logger.debug(f"Branch {branch_name} exists, deleting it")
            self.git.delete_branch(branch_name, force=True)

        # Create and checkout
        logger.debug(f"Creating and checking out branch: {branch_name}")
        self.git.checkout(branch_name, create=True)
        logger.info(f"Now on branch: {branch_name}")
        return branch_name

    def cleanup_branch(self, branch_name: str) -> None:
        """Delete an iteration branch.

        Discards any uncommitted changes before switching back to the base
        branch to prevent patch changes from polluting main.

        Args:
            branch_name: Name of the branch to delete
        """
        logger.info(f"Cleaning up branch: {branch_name}")

        # Discard uncommitted changes before switching branches
        # This prevents patch changes from traveling to main
        if not self.git.is_clean():
            logger.debug("Discarding uncommitted changes before cleanup")
            self.git.reset_hard()
            # Also remove untracked files (newly created files)
            self.git.clean()

        # Checkout base first
        logger.debug(f"Checking out base branch: {self.base_branch}")
        self.git.checkout(self.base_branch)

        # Delete the branch
        if self.git.branch_exists(branch_name):
            logger.debug(f"Deleting branch: {branch_name}")
            self.git.delete_branch(branch_name, force=True)
            logger.info(f"Deleted branch: {branch_name}")
        else:
            logger.debug(f"Branch {branch_name} does not exist, skipping delete")

        logger.info(f"Now on branch: {self.base_branch}")

    def merge_to_main(self, branch_name: str) -> str:
        """Merge an iteration branch to main.

        Args:
            branch_name: Name of the branch to merge

        Returns:
            Commit hash after merge
        """
        return self.safe_merge(branch_name)

    def safe_merge(self, branch_name: str) -> str:
        """Merge an iteration branch to main with conflict safety.

        Args:
            branch_name: Name of the branch to merge

        Returns:
            Commit hash after merge

        Raises:
            SynchronizationError: If merge conflicts occur
        """
        logger.info(f"Merging branch {branch_name} to {self.base_branch}")

        # Checkout main
        logger.debug(f"Checking out base branch: {self.base_branch}")
        self.git.checkout(self.base_branch)

        try:
            # Merge the branch
            logger.debug(f"Executing merge of {branch_name}")
            self.git._run(
                "merge",
                branch_name,
                "--no-ff",
                "-m",
                f"Merge {branch_name}",
            )
            commit = self.git.get_current_commit()
            logger.info(f"Merge successful, commit: {commit[:8]}")
        except Exception as e:
            logger.error(f"Merge failed: {e}")
            # Abort merge if it failed (e.g., conflicts)
            self.git._run("merge", "--abort", check=False)
            raise

        return commit
