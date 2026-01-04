"""Branch management for the synchronizer."""

from pathlib import Path

from veridical.synchronizer.git import GitWrapper


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

        # Ensure we're on base branch
        self.git.checkout(self.base_branch)

        # Delete if exists
        if self.git.branch_exists(branch_name):
            self.git.delete_branch(branch_name, force=True)

        # Create and checkout
        self.git.checkout(branch_name, create=True)
        return branch_name

    def cleanup_branch(self, branch_name: str) -> None:
        """Delete an iteration branch.

        Args:
            branch_name: Name of the branch to delete
        """
        # Checkout base first
        self.git.checkout(self.base_branch)

        # Delete the branch
        if self.git.branch_exists(branch_name):
            self.git.delete_branch(branch_name, force=True)

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
        # Checkout main
        self.git.checkout(self.base_branch)

        try:
            # Merge the branch
            self.git._run(
                "merge",
                branch_name,
                "--no-ff",
                "-m",
                f"Merge {branch_name}",
            )
        except Exception:
            # Abort merge if it failed (e.g., conflicts)
            self.git._run("merge", "--abort", check=False)
            raise

        return self.git.get_current_commit()
