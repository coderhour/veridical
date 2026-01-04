from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from veridical.api.models import SessionState
from veridical.models.result import PatchResult, PatchStatus, VerificationResult
from veridical.supervisor.loop import Supervisor


@pytest.mark.asyncio
async def test_supervisor_one_shot_success(tmp_path) -> None:
    config = MagicMock()
    config.supervisor.max_iterations = 5
    config.git.base_branch = "main"
    config.supervisor.max_consecutive_failures = 3
    config.supervisor.stagnation_threshold = 3

    mock_client = MagicMock()

    with (
        patch("veridical.supervisor.loop.Dispatcher") as MockDispatcher,
        patch("veridical.supervisor.loop.Poller") as MockPoller,
        patch("veridical.supervisor.loop.Synchronizer") as MockSynchronizer,
        patch("veridical.supervisor.loop.Verifier") as MockVerifier,
    ):
        # Setup mocks
        mock_disp = MockDispatcher.return_value
        session = MagicMock()
        session.session_id = "sess_1"
        mock_disp.create_session = AsyncMock(return_value=session)
        mock_disp.build_prompt.return_value = "prompt"

        mock_poller = MockPoller.return_value
        poll_result = MagicMock()
        poll_result.final_state = SessionState.COMPLETED
        mock_poller.wait_for_completion = AsyncMock(return_value=poll_result)

        mock_sync = MockSynchronizer.return_value
        patch_res = PatchResult(
            success=True, status=PatchStatus.APPLIED, files_changed=[], diff_hash="hash1"
        )
        mock_sync.apply_session_patch = AsyncMock(return_value=patch_res)
        mock_sync.create_iteration_branch.return_value = "iter-1"
        mock_sync.merge_to_main.return_value = "new_commit_hash"

        mock_verifier = MockVerifier.return_value
        verify_res = VerificationResult(passed=True, gates=[], duration_seconds=1.0)
        mock_verifier.run_all = AsyncMock(return_value=verify_res)

        # Run
        supervisor = Supervisor(config, mock_client, tmp_path)
        result = await supervisor.run("Fix bug")

        assert result.success
        assert result.iterations == 1
        assert result.final_commit == "new_commit_hash"

        mock_disp.create_session.assert_called_once()
        mock_verifier.run_all.assert_called_once()


@pytest.mark.asyncio
async def test_supervisor_iterative_repair(tmp_path) -> None:
    config = MagicMock()
    config.supervisor.max_iterations = 5
    config.git.base_branch = "main"
    config.supervisor.max_consecutive_failures = 3
    config.supervisor.stagnation_threshold = 3
    mock_client = MagicMock()

    with (
        patch("veridical.supervisor.loop.Dispatcher") as MockDispatcher,
        patch("veridical.supervisor.loop.Poller") as MockPoller,
        patch("veridical.supervisor.loop.Synchronizer") as MockSynchronizer,
        patch("veridical.supervisor.loop.Verifier") as MockVerifier,
    ):
        mock_disp = MockDispatcher.return_value
        session = MagicMock()
        session.session_id = "sess_1"
        mock_disp.create_session = AsyncMock(return_value=session)
        mock_disp.build_prompt.side_effect = ["p1", "p2"]

        mock_poller = MockPoller.return_value
        poll_result = MagicMock()
        poll_result.final_state = SessionState.COMPLETED
        mock_poller.wait_for_completion = AsyncMock(return_value=poll_result)

        mock_sync = MockSynchronizer.return_value
        patch_res = PatchResult(
            success=True, status=PatchStatus.APPLIED, files_changed=[], diff_hash="hash2"
        )
        mock_sync.apply_session_patch = AsyncMock(return_value=patch_res)
        mock_sync.create_iteration_branch.side_effect = ["iter-1", "iter-2"]
        mock_sync.merge_to_main.return_value = "final_hash"

        mock_verifier = MockVerifier.return_value
        # Fail first, pass second
        fail_res = VerificationResult(passed=False, gates=[], duration_seconds=1.0)
        pass_res = VerificationResult(passed=True, gates=[], duration_seconds=1.0)

        # Async side effect handling
        iter_count = 0

        async def verify_side_effect(*_args, **_kwargs):
            nonlocal iter_count
            iter_count += 1
            if iter_count == 1:
                return fail_res
            return pass_res

        mock_verifier.run_all.side_effect = verify_side_effect

        mock_verifier.generate_feedback.return_value = "Error info"

        supervisor = Supervisor(config, mock_client, tmp_path)
        result = await supervisor.run("Fix bug")

        assert result.success
        assert result.iterations == 2

        assert mock_disp.create_session.call_count == 2
        # Mock calls might be out of order in assert_has_calls usage, but explicit checking is fine
        # Verify second prompt build included error context
        mock_disp.build_prompt.assert_called_with("Fix bug", "Error info")


@pytest.mark.asyncio
async def test_supervisor_circuit_breaker(tmp_path) -> None:
    config = MagicMock()
    config.supervisor.max_iterations = 2
    config.git.base_branch = "main"
    config.supervisor.max_consecutive_failures = 3
    config.supervisor.stagnation_threshold = 3

    mock_client = MagicMock()

    with (
        patch("veridical.supervisor.loop.Dispatcher") as MockDispatcher,
        patch("veridical.supervisor.loop.Poller") as MockPoller,
        patch("veridical.supervisor.loop.Synchronizer") as MockSynchronizer,
        patch("veridical.supervisor.loop.Verifier") as MockVerifier,
    ):
        mock_disp = MockDispatcher.return_value
        mock_disp.create_session = AsyncMock(return_value=MagicMock())

        mock_poller = MockPoller.return_value
        poll_result = MagicMock()
        poll_result.final_state = SessionState.COMPLETED
        mock_poller.wait_for_completion = AsyncMock(return_value=poll_result)

        mock_sync = MockSynchronizer.return_value
        patch_res = PatchResult(
            success=True, status=PatchStatus.APPLIED, files_changed=[], diff_hash="hash"
        )
        mock_sync.apply_session_patch = AsyncMock(return_value=patch_res)

        mock_verifier = MockVerifier.return_value
        fail_res = VerificationResult(passed=False, gates=[], duration_seconds=1.0)
        mock_verifier.run_all = AsyncMock(return_value=fail_res)
        mock_verifier.generate_feedback.return_value = "Error"

        supervisor = Supervisor(config, mock_client, tmp_path)
        result = await supervisor.run("Task")

        assert not result.success
        assert result.iterations == 3
        assert "Maximum iterations" in result.failure_reason
