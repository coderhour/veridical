"""Branch management for the synchronizer."""

import logging
from pathlib import Path

from veridical.synchronizer.git import GitWrapper

logger = logging.getLogger(__name__)


def sanitize_branch_name(name: str) -> str:
    """Sanitize a string to create a valid Git branch name.

    Converts to lowercase, replaces spaces/underscores with hyphens,
    and removes non-alphanumeric characters (except hyphens).

    Args:
        name: Input string to sanitize

    Returns:
        Sanitized branch name containing only [a-z0-9-]
    """
    # Convert to lowercase
    sanitized = name.lower()

    # Replace spaces and underscores with hyphens
    sanitized = sanitized.replace(" ", "-").replace("_", "-")

    # Keep only alphanumeric and hyphens
    sanitized = "".join(c for c in sanitized if c.isalnum() or c == "-")

    # Remove leading/trailing hyphens and collapse multiple hyphens
    sanitized = "-".join(part for part in sanitized.split("-") if part)

    # Fallback if empty
    return sanitized if sanitized else "veridical-work"


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

        # Capture the starting branch
        current_branch = self.git.get_current_branch()
        if current_branch:
            self.starting_branch = current_branch
            logger.info(f"Starting branch: {self.starting_branch}")
        else:
            # Detached HEAD state - fall back to base_branch
            self.starting_branch = base_branch
            logger.warning(
                f"Detached HEAD detected, using base_branch '{base_branch}' as starting branch"
            )

    def get_iteration_branch_name(self, iteration: int) -> str:
        """Get the branch name for an iteration.

        Args:
            iteration: Iteration number

        Returns:
            Branch name
        """
        return f"{self.branch_prefix}{iteration}"

    def create_work_branch(self, task_description: str, prefix: str = "feat") -> str:
        """Create or checkout a work branch for the task.

        Args:
            task_description: Description of the task (used for branch naming)
            prefix: Branch prefix ('feat' or 'fix')

        Returns:
            Name of the work branch
        """
        # Sanitize the task description to create a branch name
        sanitized_name = sanitize_branch_name(task_description)
        branch_name = f"{prefix}/{sanitized_name}"

        logger.info(f"Work branch: {branch_name}")

        # Check if branch already exists
        if self.git.branch_exists(branch_name):
            logger.info(f"Work branch {branch_name} already exists, checking it out")
            self.git.checkout(branch_name)
        else:
            # Create from base_branch
            logger.info(f"Creating work branch {branch_name} from {self.base_branch}")
            self.git.checkout(self.base_branch)
            self.git.checkout(branch_name, create=True)

        return branch_name

    def create_iteration_branch(self, iteration: int, base_commit: str | None = None) -> str:
        """Create and checkout an iteration branch.

        If the branch already exists, it will be deleted and recreated.

        Args:
            iteration: Iteration number
            base_commit: Optional commit to branch from instead of the base branch.
                         Used when applying a patch that was generated against a
                         specific commit (e.g. from a resumed Jules session).

        Returns:
            Name of the created branch
        """
        branch_name = self.get_iteration_branch_name(iteration)
        logger.info(f"Creating iteration branch: {branch_name}")

        # Determine the starting point
        start_ref = base_commit or self.base_branch
        if base_commit:
            logger.info(f"Branching from base commit: {base_commit[:12]}")
        else:
            logger.debug(f"Checking out base branch: {self.base_branch}")

        self.git.checkout(start_ref)

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
