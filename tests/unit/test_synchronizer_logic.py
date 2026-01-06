from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from veridical.api.client import JulesClient
from veridical.synchronizer.branch import BranchManager
from veridical.synchronizer.patch import Synchronizer


@pytest.mark.unit
class TestJulesClientPatch:
    @pytest.mark.asyncio
    async def test_download_patch(self, respx_mock) -> None:
        client = JulesClient(api_key="test")
        session_id = "sess_123"
        diff_content = "diff --git a/foo.py b/foo.py\n..."

        respx_mock.get(
            f"https://jules.googleapis.com/v1alpha/sessions/{session_id}/activities"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "activities": [
                        {"artifacts": [{"changeSet": {"gitPatch": {"unidiffPatch": diff_content}}}]}
                    ]
                },
            )
        )

        async with client:
            result = await client.download_patch(session_id)
            assert result == diff_content

    @pytest.mark.asyncio
    async def test_download_patch_empty(self, respx_mock) -> None:
        client = JulesClient(api_key="test")
        session_id = "sess_123"

        respx_mock.get(
            f"https://jules.googleapis.com/v1alpha/sessions/{session_id}/activities"
        ).mock(return_value=httpx.Response(200, json={"activities": []}))

        async with client:
            result = await client.download_patch(session_id)
            assert result == ""


@pytest.mark.unit
class TestSynchronizerLogic:
    @pytest.mark.asyncio
    async def test_apply_session_patch(self) -> None:
        with (
            patch("veridical.synchronizer.patch.GitWrapper"),
            patch("veridical.synchronizer.patch.BranchManager"),
            patch("veridical.synchronizer.patch.PatchApplier") as MockApplier,
        ):
            mock_applier = MockApplier.return_value
            mock_applier.apply_patch.return_value = MagicMock(success=True)

            config = MagicMock()
            config.git.base_branch = "main"

            synchronizer = Synchronizer(config, Path("/tmp"))

            client = MagicMock()
            client.download_patch = AsyncMock(return_value="raw_diff")

            result = await synchronizer.apply_session_patch(client, "sess_1")

            client.download_patch.assert_awaited_once_with("sess_1")
            mock_applier.apply_patch.assert_called_once_with("raw_diff", skip_review=False)
            assert result.success

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
            mock_manager.create_iteration_branch.assert_called_once_with(123)


@pytest.mark.unit
class TestBranchManager:
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
