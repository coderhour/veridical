"""Git operations wrapper."""

import hashlib
import subprocess
from pathlib import Path

from veridical.exceptions import SynchronizationError


class GitWrapper:
    """Wrapper for git command-line operations.

    Provides a clean interface for git operations needed by Veridical,
    with proper error handling and output capture.
    """

    def __init__(self, repo_path: Path) -> None:
        """Initialize the git wrapper.

        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = repo_path

    def _run(
        self,
        *args: str,
        check: bool = True,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command.

        Args:
            *args: Git command arguments
            check: Whether to check return code
            capture_output: Whether to capture stdout/stderr

        Returns:
            Completed process result

        Raises:
            SynchronizationError: If command fails and check is True
        """
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.repo_path,
                check=check,
                capture_output=capture_output,
                text=True,
            )
            return result
        except subprocess.CalledProcessError as e:
            raise SynchronizationError(
                f"Git command failed: git {' '.join(args)}",
                operation=" ".join(args[:2]),
                details=e.stderr or str(e),
            ) from e

    def get_current_branch(self) -> str:
        """Get the current branch name.

        Returns:
            Name of the current branch
        """
        result = self._run("branch", "--show-current")
        return result.stdout.strip()

    def get_current_commit(self) -> str:
        """Get the current commit hash.

        Returns:
            Full commit hash
        """
        result = self._run("rev-parse", "HEAD")
        return result.stdout.strip()

    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists.

        Args:
            branch_name: Name of the branch to check

        Returns:
            True if branch exists
        """
        result = self._run(
            "branch",
            "--list",
            branch_name,
            check=False,
        )
        return bool(result.stdout.strip())

    def checkout(self, ref: str, *, create: bool = False) -> None:
        """Checkout a branch or commit.

        Args:
            ref: Branch name or commit to checkout
            create: Whether to create a new branch
        """
        if create:
            self._run("checkout", "-b", ref)
        else:
            self._run("checkout", ref)

    def delete_branch(self, branch_name: str, *, force: bool = False) -> None:
        """Delete a branch.

        Args:
            branch_name: Name of the branch to delete
            force: Whether to force delete
        """
        flag = "-D" if force else "-d"
        self._run("branch", flag, branch_name)

    def get_diff(self, staged: bool = False) -> str:
        """Get the current diff.

        Args:
            staged: Whether to get staged changes only

        Returns:
            Diff output
        """
        result = self._run("diff", "--staged") if staged else self._run("diff")
        return result.stdout

    def get_diff_stat(self) -> list[str]:
        """Get list of changed files.

        Returns:
            List of file paths that have changes
        """
        result = self._run("diff", "--name-only")
        return [f for f in result.stdout.strip().split("\n") if f]

    def compute_diff_hash(self) -> str:
        """Compute a hash of the current diff.

        Returns:
            SHA256 hash of the diff content
        """
        diff = self.get_diff()
        return hashlib.sha256(diff.encode()).hexdigest()[:16]

    def add_all(self) -> None:
        """Stage all changes."""
        self._run("add", "-A")

    def commit(self, message: str) -> str:
        """Create a commit.

        Args:
            message: Commit message

        Returns:
            Commit hash
        """
        self._run("commit", "-m", message)
        return self.get_current_commit()

    def is_clean(self) -> bool:
        """Check if the working directory is clean.

        Returns:
            True if no uncommitted changes
        """
        result = self._run("status", "--porcelain")
        return not result.stdout.strip()

    def get_remote_url(self, remote: str = "origin") -> str:
        """Get the URL of a git remote.

        Args:
            remote: Name of the remote (default: "origin")

        Returns:
            Remote URL
        """
        result = self._run("remote", "get-url", remote)
        return result.stdout.strip()
