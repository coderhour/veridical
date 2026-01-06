"""Human review management for the synchronizer.

Handles prompting for human approval and tracking approved files
across iterations to avoid redundant prompts.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

logger = logging.getLogger(__name__)


@dataclass
class FileApproval:
    """Tracks approval status for a single file."""

    file_path: str
    content_hash: str
    approved: bool = False


@dataclass
class ReviewManager:
    """Manages human review approvals for file changes.

    Tracks which files have been approved and their content hashes
    to avoid prompting for unchanged files in subsequent iterations.
    """

    console: Console = field(default_factory=Console)
    _approvals: dict[str, FileApproval] = field(default_factory=dict)

    def compute_file_hash(self, repo_path: Path, file_path: str) -> str:
        """Compute a hash of file content for change detection.

        Args:
            repo_path: Path to the repository root
            file_path: Relative path to the file

        Returns:
            SHA256 hash of the file content, or empty string if file doesn't exist
        """
        full_path = repo_path / file_path
        if not full_path.exists():
            return ""
        content = full_path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def compute_patch_hash(self, patch_content: str, file_path: str) -> str:
        """Compute a hash representing the file's change in a patch.

        Extracts the relevant portion of the patch for the given file
        and computes a hash of it.

        Args:
            patch_content: Full unified diff patch content
            file_path: Path to the specific file

        Returns:
            SHA256 hash of the file's portion of the patch
        """
        # Extract the diff section for this specific file
        lines = patch_content.splitlines(keepends=True)
        file_diff_lines = []
        in_file_section = False

        for line in lines:
            if line.startswith("diff --git"):
                # Check if this diff is for our file
                if f"b/{file_path}" in line:
                    in_file_section = True
                    file_diff_lines = [line]
                else:
                    in_file_section = False
            elif in_file_section:
                file_diff_lines.append(line)

        diff_content = "".join(file_diff_lines)
        return hashlib.sha256(diff_content.encode()).hexdigest()

    def get_files_needing_review(
        self,
        review_files: list[str],
        patch_content: str,
    ) -> list[str]:
        """Filter out files that have already been approved with same content.

        Args:
            review_files: List of files that require review
            patch_content: The unified diff patch content

        Returns:
            List of files that still need user approval
        """
        needs_review = []

        for file_path in review_files:
            current_hash = self.compute_patch_hash(patch_content, file_path)

            if file_path in self._approvals:
                approval = self._approvals[file_path]
                if approval.approved and approval.content_hash == current_hash:
                    logger.debug(f"File {file_path} already approved with same content, skipping")
                    continue

            needs_review.append(file_path)

        return needs_review

    def is_fully_approved(
        self,
        review_files: list[str],
        patch_content: str,
    ) -> bool:
        """Check if all files in the list have been approved.

        Args:
            review_files: List of files that require review
            patch_content: The unified diff patch content

        Returns:
            True if all files are approved, False otherwise
        """
        return len(self.get_files_needing_review(review_files, patch_content)) == 0

    def record_approval(
        self,
        file_path: str,
        patch_content: str,
        approved: bool = True,
    ) -> None:
        """Record the approval status for a file.

        Args:
            file_path: Path to the file
            patch_content: The unified diff patch content
            approved: Whether the file was approved
        """
        content_hash = self.compute_patch_hash(patch_content, file_path)
        self._approvals[file_path] = FileApproval(
            file_path=file_path,
            content_hash=content_hash,
            approved=approved,
        )
        logger.info(f"Recorded {'approval' if approved else 'rejection'} for {file_path}")

    def prompt_for_review(
        self,
        files: list[str],
        patch_content: str,
        repo_path: Path | None = None,  # noqa: ARG002
    ) -> bool:
        """Prompt the user to review and approve files.

        Displays the files requiring review and asks for confirmation.
        If approved, records the approval for each file.

        Args:
            files: List of files requiring review
            patch_content: The unified diff patch content
            repo_path: Optional path to repo root (for showing file diff)

        Returns:
            True if the user approved all files, False if rejected
        """
        if not files:
            return True

        files_needing_review = self.get_files_needing_review(files, patch_content)

        if not files_needing_review:
            logger.info("All files already approved, continuing")
            return True

        # Build the review table
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("#", style="dim", width=4)
        table.add_column("File", style="cyan")
        table.add_column("Status", style="yellow")

        for i, file_path in enumerate(files_needing_review, 1):
            table.add_row(str(i), file_path, "⚠️ Requires Review")

        # Show the panel
        self.console.print()
        self.console.print(
            Panel(
                table,
                title="[bold yellow]🔍 Human Review Required[/bold yellow]",
                subtitle="[dim]The following files need your approval before continuing[/dim]",
                border_style="yellow",
            )
        )

        # Show the diff for each file
        self.console.print()
        self.console.print("[bold]Changes to review:[/bold]")

        for file_path in files_needing_review:
            file_diff = self._extract_file_diff(patch_content, file_path)
            if file_diff:
                self.console.print()
                self.console.print(f"[cyan]{file_path}[/cyan]:")
                syntax = Syntax(
                    file_diff.strip(),
                    "diff",
                    theme="monokai",
                    line_numbers=True,
                )
                self.console.print(syntax)

        # Prompt for approval
        self.console.print()
        try:
            approved = typer.confirm(
                "Do you approve these changes?",
                default=False,
            )
        except typer.Abort:
            approved = False

        # Record the decision for each file
        for file_path in files_needing_review:
            self.record_approval(file_path, patch_content, approved=approved)

        if approved:
            self.console.print("[green]✓ Changes approved, continuing...[/green]")
        else:
            self.console.print("[red]✗ Changes rejected, aborting...[/red]")

        return approved

    def _extract_file_diff(self, patch_content: str, file_path: str) -> str:
        """Extract the diff section for a specific file.

        Args:
            patch_content: Full unified diff patch content
            file_path: Path to the specific file

        Returns:
            The diff section for the file
        """
        lines = patch_content.splitlines()
        file_diff_lines = []
        in_file_section = False

        for line in lines:
            if line.startswith("diff --git"):
                if f"b/{file_path}" in line:
                    in_file_section = True
                    file_diff_lines = [line]
                else:
                    if in_file_section:
                        # We've reached the next file, stop
                        break
            elif in_file_section:
                file_diff_lines.append(line)

        return "\n".join(file_diff_lines)

    def clear_approvals(self) -> None:
        """Clear all recorded approvals."""
        self._approvals.clear()
        logger.debug("Cleared all file approvals")
