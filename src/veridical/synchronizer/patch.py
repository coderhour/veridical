"""Patch application for the synchronizer."""

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from veridical.models.result import PatchResult, PatchStatus
from veridical.synchronizer.branch import BranchManager
from veridical.synchronizer.git import GitWrapper
from veridical.synchronizer.review import ReviewManager
from veridical.synchronizer.validator import ScopeValidator

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from rich.console import Console

    from veridical.api.client import JulesClient
    from veridical.config.schema import ScopeValidationConfig, VeridicalConfig


class PatchApplier:
    """Applies patches from Jules to the local repository."""

    def __init__(
        self,
        repo_path: Path,
        validation_config: "ScopeValidationConfig",
        review_manager: ReviewManager | None = None,
    ) -> None:
        """Initialize the patch applier.

        Args:
            repo_path: Path to the repository root
            validation_config: Scope validation configuration
            review_manager: Optional review manager for tracking approvals
        """
        self.repo_path = repo_path
        self.git = GitWrapper(repo_path)
        self.validator = ScopeValidator(validation_config)
        self.strict_mode = validation_config.strict_mode
        self.review_manager = review_manager
        self._pending_patch: str | None = None

    @property
    def pending_patch(self) -> str | None:
        """Get the pending patch data awaiting review."""
        return self._pending_patch

    def apply_patch(
        self,
        patch_data: str,
        skip_review: bool = False,
    ) -> PatchResult:
        """Apply a patch to the repository.

        Args:
            patch_data: Unified diff patch content
            skip_review: If True, skip human review check (files already approved)

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

        # Validate patch scope before applying
        validation_result = self.validator.validate_patch(patch_data)
        if not validation_result.is_valid:
            violations_str = "\n".join(f"- {v}" for v in validation_result.violations)
            error_msg = f"Patch rejected due to scope violations:\n{violations_str}"
            if self.strict_mode:
                logger.error(error_msg)
                return PatchResult.failed(error_msg, status=PatchStatus.REJECTED)
            else:
                logger.warning(f"Scope violations found (non-strict mode):\n{violations_str}")

        # Check if human review is required for any files
        if validation_result.review_required and not skip_review:
            review_files = validation_result.review_required

            # Check if all files are already approved
            if self.review_manager and self.review_manager.is_fully_approved(
                review_files, patch_data
            ):
                logger.info("All files already approved, proceeding with patch")
            else:
                # Store the pending patch for later application after approval
                self._pending_patch = patch_data
                files_str = ", ".join(review_files)
                logger.info(f"Patch requires human approval for: {files_str}")
                return PatchResult.pending_review(
                    review_required_files=review_files,
                )

        try:
            logger.info("Applying patch...")
            # Write patch to temp file and apply
            patch_file = self.repo_path / ".veridical_patch.tmp"
            patch_file.write_text(patch_data)

            try:
                subprocess.run(
                    ["git", "apply", "--3way", "--whitespace=fix", str(patch_file)],
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

            logger.info(
                "Patch applied successfully.",
                extra={"files_changed": files, "diff_hash": diff_hash},
            )
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
        console: "Console | None" = None,
    ) -> None:
        """Initialize the synchronizer.

        Args:
            config: Veridical configuration
            repo_path: Path to the repository root
            console: Optional rich console for user interaction
        """
        from rich.console import Console as RichConsole

        self.config = config
        self.repo_path = repo_path
        self.console = console or RichConsole()
        self.git = GitWrapper(repo_path)
        self.branch_manager = BranchManager(
            repo_path,
            base_branch=config.git.base_branch,
            branch_prefix=config.git.branch_prefix,
        )
        self.review_manager = ReviewManager(console=self.console)
        self.patch_applier = PatchApplier(
            repo_path,
            validation_config=config.git.scope_validation,
            review_manager=self.review_manager,
        )
        self._work_branch: str | None = None
        self._target_branch_override: str | None = None

    @property
    def starting_branch(self) -> str:
        """Get the starting branch captured at initialization."""
        return self.branch_manager.starting_branch

    @property
    def work_branch(self) -> str | None:
        """Get the work branch created for this run."""
        return self._work_branch

    def setup_work_branch(
        self,
        task_description: str,
        target_branch: str | None = None,
    ) -> None:
        """Set up the work branch for this run.

        Args:
            task_description: Description of the task (for branch naming)
            target_branch: Optional override for the target branch
        """
        self._target_branch_override = target_branch

        if target_branch:
            # Explicit override - use it as the work branch
            logger.info(f"Using explicit target branch: {target_branch}")
            self._work_branch = target_branch
            # Ensure it exists and checkout
            if not self.git.branch_exists(target_branch):
                logger.info(
                    f"Creating target branch {target_branch} from {self.config.git.base_branch}"
                )
                self.git.checkout(self.config.git.base_branch)
                self.git.checkout(target_branch, create=True)
            else:
                self.git.checkout(target_branch)
        elif self.config.git.auto_create_work_branch:
            # Auto-create work branch from task description
            logger.info("Auto-creating work branch")
            self._work_branch = self.branch_manager.create_work_branch(
                task_description, prefix="feat"
            )
        else:
            # Legacy behavior - merge to base_branch
            logger.info(f"Auto-create disabled, using base_branch: {self.config.git.base_branch}")
            self._work_branch = self.config.git.base_branch
            self.git.checkout(self._work_branch)

        # Update branch manager's base branch so iterations are created from the target
        self.branch_manager.base_branch = self._work_branch

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

    def apply_patch(self, patch_data: str, skip_review: bool = False) -> PatchResult:
        """Apply a patch to the current branch.

        Args:
            patch_data: Unified diff patch content
            skip_review: If True, skip human review check (files already approved)

        Returns:
            Result of the patch application
        """
        return self.patch_applier.apply_patch(patch_data, skip_review=skip_review)

    def prompt_human_review(
        self,
        review_files: list[str],
        patch_content: str,
    ) -> bool:
        """Prompt the user to review and approve files.

        Args:
            review_files: List of files requiring review
            patch_content: The unified diff patch content

        Returns:
            True if the user approved all files, False if rejected
        """
        return self.review_manager.prompt_for_review(review_files, patch_content, self.repo_path)

    def apply_pending_patch(self) -> PatchResult:
        """Apply the pending patch after human approval.

        Returns:
            Result of the patch application
        """
        if not self.patch_applier.pending_patch:
            return PatchResult.failed("No pending patch to apply")

        patch_data = self.patch_applier.pending_patch
        self.patch_applier._pending_patch = None
        return self.apply_patch(patch_data, skip_review=True)

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

    def merge_to_main(self, branch_name: str, task_description: str | None = None) -> str:
        """Merge a successful iteration to the target branch.

        Commits any uncommitted changes first, then merges the branch.
        The target branch is determined by:
        1. Explicit --target-branch override
        2. Auto-created work branch (if auto_create_work_branch is enabled)
        3. base_branch (legacy behavior)

        Args:
            branch_name: Name of the branch to merge
            task_description: Description of the task for the commit message

        Returns:
            Commit hash after merge
        """
        # Determine the merge target
        target = self._work_branch or self.config.git.base_branch
        logger.info(f"Synchronizer: preparing to merge {branch_name} to {target}")

        # Commit changes on the iteration branch before merging
        # (patches are applied as uncommitted changes)
        if not self.git.is_clean():
            logger.info("Uncommitted changes found, committing before merge")
            if task_description:
                commit_msg = f"Veridical: {task_description}"
            else:
                commit_msg = f"Veridical: verified changes from {branch_name}"
            self.commit_changes(commit_msg)
        else:
            logger.debug("Working directory is clean, no commit needed")

        # Checkout target branch and merge
        logger.info(f"Checking out target branch: {target}")
        self.git.checkout(target)
        logger.info(f"Merging {branch_name} into {target}")
        self.git._run(
            "merge",
            branch_name,
            "--no-ff",
            "-m",
            f"Merge {branch_name}",
        )
        commit = self.git.get_current_commit()

        # Auto cleanup if configured
        if self.config.git.auto_cleanup and self.git.branch_exists(branch_name):
            logger.info(f"Auto-cleanup enabled, deleting branch {branch_name}")
            self.git.delete_branch(branch_name, force=True)

        # Return to starting branch
        logger.info(f"Returning to starting branch: {self.starting_branch}")
        self.git.checkout(self.starting_branch)

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
