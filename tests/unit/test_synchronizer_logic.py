from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from veridical.api.client import JulesClient
from veridical.api.models import GitPatch
from veridical.models.result import PatchResult
from veridical.synchronizer.branch import BranchManager
from veridical.synchronizer.patch import Synchronizer


@pytest.mark.unit
class TestJulesClientPatch:
    @pytest.mark.asyncio
    async def test_download_patch(self, respx_mock) -> None:
        client = JulesClient(api_key="test")
        session_id = "sess_123"
        diff_content = "diff --git a/foo.py b/foo.py\n..."
        base_commit = "abc123def456"

        respx_mock.get(
            f"https://jules.googleapis.com/v1alpha/sessions/{session_id}/activities"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "activities": [
                        {
                            "artifacts": [
                                {
                                    "changeSet": {
                                        "gitPatch": {
                                            "unidiffPatch": diff_content,
                                            "baseCommitId": base_commit,
                                        }
                                    }
                                }
                            ]
                        }
                    ]
                },
            )
        )

        async with client:
            result = await client.download_patch(session_id)
            assert isinstance(result, GitPatch)
            assert result.unidiff_patch == diff_content
            assert result.base_commit_id == base_commit

    @pytest.mark.asyncio
    async def test_download_patch_empty(self, respx_mock) -> None:
        client = JulesClient(api_key="test")
        session_id = "sess_123"

        respx_mock.get(
            f"https://jules.googleapis.com/v1alpha/sessions/{session_id}/activities"
        ).mock(return_value=httpx.Response(200, json={"activities": []}))

        async with client:
            result = await client.download_patch(session_id)
            assert isinstance(result, GitPatch)
            assert result.unidiff_patch is None


@pytest.mark.unit
class TestSynchronizerLogic:
    @pytest.fixture(autouse=True)
    def mock_logger(self):
        """Mock logger to prevent 'I/O operation on closed file' errors."""
        with patch("veridical.synchronizer.patch.logger") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_apply_session_patch(self) -> None:
        with (
            patch("veridical.synchronizer.patch.GitWrapper"),
            patch("veridical.synchronizer.patch.BranchManager") as MockManager,
            patch("veridical.synchronizer.patch.PatchApplier") as MockApplier,
        ):
            mock_manager = MockManager.return_value
            mock_manager.create_iteration_branch.return_value = "veridical/iter-1"
            mock_applier = MockApplier.return_value
            mock_applier.apply_patch.return_value = MagicMock(success=True)

            config = MagicMock()
            config.git.base_branch = "main"

            synchronizer = Synchronizer(config, Path("/tmp"))

            git_patch = GitPatch(unidiff_patch="raw_diff", base_commit_id="abc123")
            client = MagicMock()
            client.download_patch = AsyncMock(return_value=git_patch)

            iter_branch, result = await synchronizer.apply_session_patch(client, "sess_1", 1)

            client.download_patch.assert_awaited_once_with("sess_1")
            mock_manager.create_iteration_branch.assert_called_once_with(1, base_commit="abc123")
            mock_applier.apply_patch.assert_called_once_with("raw_diff", skip_review=False)
            assert iter_branch == "veridical/iter-1"
            assert result.success

    @pytest.mark.asyncio
    async def test_apply_session_patch_without_base_commit(self) -> None:
        """Test apply_session_patch when GitPatch has no base_commit_id."""
        with (
            patch("veridical.synchronizer.patch.GitWrapper"),
            patch("veridical.synchronizer.patch.BranchManager") as MockManager,
            patch("veridical.synchronizer.patch.PatchApplier") as MockApplier,
        ):
            mock_manager = MockManager.return_value
            mock_manager.create_iteration_branch.return_value = "veridical/iter-1"
            mock_applier = MockApplier.return_value
            mock_applier.apply_patch.return_value = MagicMock(
                success=True, files_changed=["a.py"], diff_hash="h1"
            )

            config = MagicMock()
            config.git.base_branch = "main"

            synchronizer = Synchronizer(config, Path("/tmp"))

            git_patch = GitPatch(unidiff_patch="raw_diff")
            client = MagicMock()
            client.download_patch = AsyncMock(return_value=git_patch)

            iter_branch, result = await synchronizer.apply_session_patch(client, "sess_1", 1)

            # base_commit should be None
            mock_manager.create_iteration_branch.assert_called_once_with(1, base_commit=None)
            assert iter_branch == "veridical/iter-1"
            assert result.success

    @pytest.mark.asyncio
    async def test_apply_session_patch_builds_patch_summary(self) -> None:
        """Test that patch_summary is built from GitPatch metadata and files_changed."""
        with (
            patch("veridical.synchronizer.patch.GitWrapper"),
            patch("veridical.synchronizer.patch.BranchManager") as MockManager,
            patch("veridical.synchronizer.patch.PatchApplier") as MockApplier,
        ):
            mock_manager = MockManager.return_value
            mock_manager.create_iteration_branch.return_value = "veridical/iter-1"
            mock_applier = MockApplier.return_value
            mock_applier.apply_patch.return_value = PatchResult.applied(
                files_changed=["src/main.py", "README.md"], diff_hash="h1"
            )

            config = MagicMock()
            config.git.base_branch = "main"

            synchronizer = Synchronizer(config, Path("/tmp"))

            git_patch = GitPatch(
                unidiff_patch="raw_diff",
                base_commit_id="abc123def456",
                suggested_commit_message="Fix the bug",
            )
            client = MagicMock()
            client.download_patch = AsyncMock(return_value=git_patch)

            _, result = await synchronizer.apply_session_patch(client, "sess_1", 1)

            assert result.patch_summary is not None
            assert "Base commit: abc123def456" in result.patch_summary
            assert "Message: Fix the bug" in result.patch_summary
            assert "Files changed (2):" in result.patch_summary
            assert "  - src/main.py" in result.patch_summary
            assert "  - README.md" in result.patch_summary

    @pytest.mark.asyncio
    async def test_apply_session_patch_no_summary_on_failure(self) -> None:
        """Test that patch_summary is not set when patch application fails."""
        with (
            patch("veridical.synchronizer.patch.GitWrapper"),
            patch("veridical.synchronizer.patch.BranchManager") as MockManager,
            patch("veridical.synchronizer.patch.PatchApplier") as MockApplier,
        ):
            mock_manager = MockManager.return_value
            mock_manager.create_iteration_branch.return_value = "veridical/iter-1"
            mock_applier = MockApplier.return_value
            mock_applier.apply_patch.return_value = PatchResult.failed(error="patch does not apply")

            config = MagicMock()
            config.git.base_branch = "main"

            synchronizer = Synchronizer(config, Path("/tmp"))

            git_patch = GitPatch(unidiff_patch="bad_diff", base_commit_id="abc123")
            client = MagicMock()
            client.download_patch = AsyncMock(return_value=git_patch)

            _, result = await synchronizer.apply_session_patch(client, "sess_1", 1)

            assert not result.success
            assert result.patch_summary is None

    def test_create_iteration_branch(self) -> None:
        with (
            patch("veridical.synchronizer.patch.GitWrapper"),
            patch("veridical.synchronizer.patch.BranchManager") as MockManager,
            patch("veridical.synchronizer.patch.PatchApplier"),
        ):
            mock_manager = MockManager.return_value
            mock_manager.create_iteration_branch.return_value = "custom-prefix-123"

            config = MagicMock()
            config.git.base_branch = "main"

            synchronizer = Synchronizer(config, Path("/tmp"))
            branch = synchronizer.create_iteration_branch(123)

            assert branch == "custom-prefix-123"
            mock_manager.create_iteration_branch.assert_called_once_with(123, base_commit=None)


@pytest.mark.unit
class TestBranchManager:
    def test_create_iteration_branch_with_base_commit(self) -> None:
        """Test that create_iteration_branch checks out the base_commit instead of base_branch."""
        with patch("veridical.synchronizer.branch.GitWrapper") as MockGit:
            mock_git = MockGit.return_value
            mock_git.branch_exists.return_value = False

            manager = BranchManager(Path("/tmp"))
            branch = manager.create_iteration_branch(1, base_commit="abc123def456")

            assert branch == "veridical/iter-1"
            # Should checkout the base_commit, not the base_branch
            mock_git.checkout.assert_any_call("abc123def456")
            mock_git.checkout.assert_any_call("veridical/iter-1", create=True)

    def test_create_iteration_branch_without_base_commit(self) -> None:
        """Test that create_iteration_branch uses base_branch when no base_commit."""
        with patch("veridical.synchronizer.branch.GitWrapper") as MockGit:
            mock_git = MockGit.return_value
            mock_git.branch_exists.return_value = False

            manager = BranchManager(Path("/tmp"))
            branch = manager.create_iteration_branch(1)

            assert branch == "veridical/iter-1"
            # Should checkout the base_branch (default "main")
            mock_git.checkout.assert_any_call("main")
            mock_git.checkout.assert_any_call("veridical/iter-1", create=True)

    def test_safe_merge_success(self) -> None:
        with patch("veridical.synchronizer.branch.GitWrapper") as MockGit:
            mock_git = MockGit.return_value
            mock_git.get_current_commit.return_value = "hash123"

            manager = BranchManager(Path("/tmp"))
            hash = manager.safe_merge("iter-1")

            assert hash == "hash123"
            mock_git._run.assert_any_call("merge", "iter-1", "--no-ff", "-m", "Merge iter-1")

    def test_safe_merge_conflict(self) -> None:
        with patch("veridical.synchronizer.branch.GitWrapper") as MockGit:
            mock_git = MockGit.return_value

            # Simulate failure on merge
            # 1. merge (fails)
            # 2. merge --abort
            mock_git._run.side_effect = [Exception("Conflict"), MagicMock()]

            manager = BranchManager(Path("/tmp"))

            try:
                manager.safe_merge("iter-1")
            except Exception as e:
                assert str(e) == "Conflict"
                # Verify calls
                assert mock_git._run.call_count == 2
                assert mock_git._run.call_args_list[0][0][0] == "merge"
                assert mock_git._run.call_args_list[1][0][0] == "merge"
                mock_git.checkout.assert_called()
                return

            pytest.fail("Did not raise Exception")

    def test_cleanup_branch_discards_uncommitted_changes(self) -> None:
        """Test that cleanup_branch discards uncommitted changes before switching.

        This prevents patch changes from polluting the main branch when checkout
        happens - git normally preserves uncommitted working directory changes
        when switching branches.
        """
        with patch("veridical.synchronizer.branch.GitWrapper") as MockGit:
            mock_git = MockGit.return_value
            # Simulate dirty working directory (uncommitted patch changes)
            mock_git.is_clean.return_value = False
            mock_git.branch_exists.return_value = True

            manager = BranchManager(Path("/tmp"))
            manager.cleanup_branch("veridical/iter-1")

            # Should reset hard to discard changes before checkout
            mock_git.reset_hard.assert_called_once()
            # Then checkout base branch
            mock_git.checkout.assert_called_once_with("main")
            # Then delete the iteration branch
            mock_git.delete_branch.assert_called_once_with("veridical/iter-1", force=True)

    def test_cleanup_branch_skips_reset_when_clean(self) -> None:
        """Test that cleanup_branch skips reset when working dir is clean."""
        with patch("veridical.synchronizer.branch.GitWrapper") as MockGit:
            mock_git = MockGit.return_value
            # Simulate clean working directory
            mock_git.is_clean.return_value = True
            mock_git.branch_exists.return_value = True

            manager = BranchManager(Path("/tmp"))
            manager.cleanup_branch("veridical/iter-1")

            # Should NOT call reset_hard
            mock_git.reset_hard.assert_not_called()
            # Should still checkout and delete
            mock_git.checkout.assert_called_once_with("main")
            mock_git.delete_branch.assert_called_once_with("veridical/iter-1", force=True)
