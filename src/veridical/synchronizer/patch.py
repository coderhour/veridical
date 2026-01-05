"""Patch application for the synchronizer."""

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from veridical.models.result import PatchResult, PatchStatus
from veridical.synchronizer.branch import BranchManager
from veridical.synchronizer.git import GitWrapper

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from veridical.api.client import JulesClient
    from veridical.config.schema import VeridicalConfig


class PatchApplier:
    """Applies patches from Jules to the local repository."""

    def __init__(self, repo_path: Path) -> None:
        """Initialize the patch applier.

        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = repo_path
        self.git = GitWrapper(repo_path)

    def apply_patch(self, patch_data: str) -> PatchResult:
        """Apply a patch to the repository.

        Args:
            patch_data: Unified diff patch content

        Returns:
            Result of the patch application
        """
        if not patch_data.strip():
            logger.info("No patch data provided, skipping application.")
            return PatchResult(
                success=True,
                status=PatchStatus.APPLIED,
                files_changed=[],
                diff_hash="",
            )

        try:
            logger.info("Applying patch...")
            # Write patch to temp file and apply
            patch_file = self.repo_path / ".veridical_patch.tmp"
            patch_file.write_text(patch_data)

            try:
                subprocess.run(
                    ["git", "apply", str(patch_file)],
                    cwd=self.repo_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logger.info("Patch applied successfully.")
            finally:
                patch_file.unlink(missing_ok=True)

            # Get changed files and diff hash
            files = self.git.get_diff_stat()
            diff_hash = self.git.compute_diff_hash()

            return PatchResult.applied(files_changed=files, diff_hash=diff_hash)

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or str(e)
            logger.error(f"Failed to apply patch: {error_msg}")
            if "conflict" in error_msg.lower():
                return PatchResult.failed(error_msg, status=PatchStatus.CONFLICT)
            return PatchResult.failed(error_msg)


class Synchronizer:
    """Main synchronizer coordinating branches and patches.

    Manages the full synchronization workflow:
    1. Create isolation branches
    2. Apply patches
    3. Clean up or merge branches
    """

    def __init__(
        self,
        config: "VeridicalConfig",
        repo_path: Path,
    ) -> None:
        """Initialize the synchronizer.

        Args:
            config: Veridical configuration
            repo_path: Path to the repository root
        """
        self.config = config
        self.repo_path = repo_path
        self.git = GitWrapper(repo_path)
        self.branch_manager = BranchManager(
            repo_path,
            base_branch=config.git.base_branch,
            branch_prefix=config.git.branch_prefix,
        )
        self.patch_applier = PatchApplier(repo_path)

    def create_iteration_branch(self, iteration: int) -> str:
        """Create and checkout an iteration branch.

        Args:
            iteration: Iteration number

        Returns:
            Name of the created branch
        """
        logger.info(f"Creating iteration branch for iteration {iteration}")
        return self.branch_manager.create_iteration_branch(iteration)

    async def apply_session_patch(
        self,
        client: "JulesClient",
        session_id: str,
    ) -> PatchResult:
        """Fetch and apply patch from a session.

        Args:
            client: API client
            session_id: Session ID

        Returns:
            Patch application result
        """
        patch_data = await client.download_patch(session_id)
        return self.apply_patch(patch_data)

    def apply_patch(self, patch_data: str) -> PatchResult:
        """Apply a patch to the current branch.

        Args:
            patch_data: Unified diff patch content

        Returns:
            Result of the patch application
        """
        return self.patch_applier.apply_patch(patch_data)

    def commit_changes(self, message: str) -> str:
        """Commit current changes.

        Args:
            message: Commit message

        Returns:
            Commit hash
        """
        self.git.add_all()
        return self.git.commit(message)

    def cleanup_branch(self, branch_name: str) -> None:
        """Clean up a failed iteration branch.

        Args:
            branch_name: Name of the branch to delete
        """
        logger.info(f"Synchronizer: cleaning up branch {branch_name}")
        self.branch_manager.cleanup_branch(branch_name)

    def merge_to_main(self, branch_name: str) -> str:
        """Merge a successful iteration to main.

        Commits any uncommitted changes first, then merges the branch.

        Args:
            branch_name: Name of the branch to merge

        Returns:
            Commit hash after merge
        """
        logger.info(f"Synchronizer: preparing to merge {branch_name} to main")

        # Commit changes on the iteration branch before merging
        # (patches are applied as uncommitted changes)
        if not self.git.is_clean():
            logger.info("Uncommitted changes found, committing before merge")
            self.commit_changes(f"Veridical: verified changes from {branch_name}")
        else:
            logger.debug("Working directory is clean, no commit needed")

        commit = self.branch_manager.merge_to_main(branch_name)

        # Auto cleanup if configured
        if self.config.git.auto_cleanup and self.git.branch_exists(branch_name):
            logger.info(f"Auto-cleanup enabled, deleting branch {branch_name}")
            self.git.delete_branch(branch_name, force=True)

        logger.info(f"Merge complete, final commit: {commit[:8]}")
        return commit

    def get_changed_files(self) -> list[str]:
        """Get list of changed files in current state.

        Returns:
            List of file paths with changes
        """
        return self.git.get_diff_stat()

    def get_diff_hash(self) -> str:
        """Get hash of current diff.

        Returns:
            Hash string for stagnation detection
        """
        return self.git.compute_diff_hash()
