"""Git utilities for checking repository state."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class GitCheckResult:
    """Result of a git status check."""

    def __init__(
        self,
        has_uncommitted: bool = False,
        has_unpushed: bool = False,
        uncommitted_files: list[str] | None = None,
        unpushed_commits: int = 0,
    ) -> None:
        self.has_uncommitted = has_uncommitted
        self.has_unpushed = has_unpushed
        self.uncommitted_files = uncommitted_files or []
        self.unpushed_commits = unpushed_commits

    @property
    def needs_attention(self) -> bool:
        """Return True if there are uncommitted or unpushed changes."""
        return self.has_uncommitted or self.has_unpushed


def check_spec_status(
    repo_path: Path | None = None,
    spec_paths: list[str] | None = None,
) -> GitCheckResult:
    """Check if there are uncommitted or unpushed changes in spec files.

    Args:
        repo_path: Path to the git repository. Defaults to current directory.
        spec_paths: List of paths to check for uncommitted changes.
                   Defaults to ["openspec/", ".veridical.yaml"].

    Returns:
        GitCheckResult with status information.
    """
    if repo_path is None:
        repo_path = Path.cwd()

    if spec_paths is None:
        spec_paths = ["openspec/"]

    result = GitCheckResult()

    try:
        # Check for uncommitted changes in spec paths
        for spec_path in spec_paths:
            full_path = repo_path / spec_path
            if not full_path.exists():
                continue

            # Check for both staged and unstaged changes
            proc = subprocess.run(
                ["git", "status", "--porcelain", str(spec_path)],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
            )

            if proc.returncode == 0 and proc.stdout.strip():
                result.has_uncommitted = True
                # Parse the output to get file names
                for line in proc.stdout.strip().split("\n"):
                    if line:
                        # Status lines are formatted as "XY filename" where XY is 2 chars
                        # The filename starts after position 2, but may have leading spaces
                        file_name = line[2:].lstrip()
                        if file_name:
                            result.uncommitted_files.append(file_name)

        # Check for unpushed commits that touch spec paths
        # First, get the current branch
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )

        if proc.returncode != 0:
            logger.debug("Could not determine current branch")
            return result

        current_branch = proc.stdout.strip()

        # Check if upstream exists
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", f"{current_branch}@{{upstream}}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )

        if proc.returncode != 0:
            # No upstream configured - this means changes haven't been pushed
            logger.debug(f"No upstream configured for branch {current_branch}")
            # If there are uncommitted changes, they definitely need pushing
            return result

        upstream = proc.stdout.strip()

        # Count unpushed commits that touch spec paths
        for spec_path in spec_paths:
            proc = subprocess.run(
                ["git", "log", f"{upstream}..HEAD", "--oneline", "--", str(spec_path)],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
            )

            if proc.returncode == 0 and proc.stdout.strip():
                commit_lines = [line for line in proc.stdout.strip().split("\n") if line]
                result.unpushed_commits += len(commit_lines)
                result.has_unpushed = True

    except FileNotFoundError:
        logger.warning("Git command not found")
    except subprocess.SubprocessError as e:
        logger.warning(f"Git command failed: {e}")

    return result


def format_spec_warning(result: GitCheckResult) -> str:
    """Format a warning message for unpushed spec changes.

    Args:
        result: The GitCheckResult to format.

    Returns:
        A formatted warning message.
    """
    lines: list[str] = []

    if result.has_uncommitted:
        lines.append("[bold yellow]⚠ Uncommitted spec changes detected![/bold yellow]")
        if result.uncommitted_files:
            lines.append("  Files with changes:")
            for f in result.uncommitted_files[:5]:  # Show first 5
                lines.append(f"    • {f}")
            if len(result.uncommitted_files) > 5:
                lines.append(f"    ... and {len(result.uncommitted_files) - 5} more files")

    if result.has_unpushed:
        lines.append("[bold yellow]⚠ Unpushed spec commits detected![/bold yellow]")
        lines.append(f"  {result.unpushed_commits} commit(s) not pushed to remote")

    if lines:
        lines.append("")
        lines.append("[dim]Jules needs specs pushed to the remote repository to access them.[/dim]")
        lines.append("[dim]Run: git push[/dim]")

    return "\n".join(lines)
