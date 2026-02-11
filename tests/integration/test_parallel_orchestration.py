"""Integration tests for parallel orchestration."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from veridical.config.schema import (
    GitConfig,
    LocalConfig,
    ParallelConfig,
    QualityGate,
    SupervisorConfig,
    VeridicalConfig,
    VerifierConfig,
)
from veridical.models.result import (
    GateResult,
    GateSeverity,
    GateStatus,
    LoopResult,
    VerificationResult,
)
from veridical.orchestrator.decomposer import Subtask, TaskDecomposer
from veridical.orchestrator.dispatcher import DispatchResult, ParallelDispatcher, WorkerResult
from veridical.orchestrator.loop import OrchestratorLoop
from veridical.orchestrator.resolver import ConflictResolver, MergeOutcome, MergeResult


@pytest.fixture
def parallel_config() -> VeridicalConfig:
    return VeridicalConfig(
        supervisor=SupervisorConfig(max_iterations=3),
        local=LocalConfig(worker_command="echo ok", gtr_enabled=True),
        verifier=VerifierConfig(
            quality_gates=[
                QualityGate(name="test-gate", command="exit 0", timeout=10, required=True),
            ],
        ),
        git=GitConfig(base_branch="main"),
        parallel=ParallelConfig(max_workers=2, final_verification=True),
    )


def _make_success_result() -> LoopResult:
    from datetime import datetime

    return LoopResult(
        success=True,
        iterations=1,
        started_at=datetime.now(),
        completed_at=datetime.now(),
    )


def _make_failure_result(reason: str = "test failure") -> LoopResult:
    from datetime import datetime

    return LoopResult.failure_result(
        iterations=2,
        started_at=datetime.now(),
        failure_reason=reason,
    )


# --------------------------------------------------------------------------
# 5.3: Integration test - 2 parallel workers complete and merge successfully
# --------------------------------------------------------------------------


class TestParallelWorkersSuccessAndMerge:
    @patch("veridical.orchestrator.loop.detect_gtr", return_value=True)
    @patch("veridical.orchestrator.loop.Verifier")
    @patch.object(ParallelDispatcher, "dispatch")
    @patch.object(ConflictResolver, "merge_branches")
    @patch.object(ConflictResolver, "cleanup_branches")
    def test_two_workers_succeed_and_merge(
        self,
        mock_cleanup: MagicMock,
        mock_merge: MagicMock,
        mock_dispatch: AsyncMock,
        mock_verifier_cls: MagicMock,
        parallel_config: VeridicalConfig,
        tmp_path: Path,
    ) -> None:
        subtasks = [
            Subtask(id="task-1", description="Add login page"),
            Subtask(id="task-2", description="Add signup page"),
        ]

        # Dispatch returns two successful workers
        mock_dispatch.return_value = DispatchResult(
            worker_results=[
                WorkerResult(
                    subtask=subtasks[0], branch="veri/task-1", result=_make_success_result()
                ),
                WorkerResult(
                    subtask=subtasks[1], branch="veri/task-2", result=_make_success_result()
                ),
            ]
        )

        # Merge succeeds
        mock_merge.return_value = MergeResult(
            outcomes=[
                MergeOutcome(branch="veri/task-1", success=True),
                MergeOutcome(branch="veri/task-2", success=True),
            ]
        )

        # Final verification passes
        mock_verifier = MagicMock()
        mock_verifier.run_all = AsyncMock(
            return_value=VerificationResult(
                passed=True,
                gates=[
                    GateResult(
                        name="test-gate",
                        status=GateStatus.PASSED,
                        severity=GateSeverity.PASS,
                        duration_seconds=0.1,
                    )
                ],
                duration_seconds=0.1,
            )
        )
        mock_verifier_cls.return_value = mock_verifier

        loop = OrchestratorLoop(parallel_config, tmp_path, max_workers=2)
        result = asyncio.run(loop.run("Build pages", subtasks=subtasks))

        assert result.success is True
        assert result.dispatch.all_succeeded is True
        assert result.merge is not None
        assert result.merge.all_merged is True
        assert result.verification_passed is True
        mock_cleanup.assert_called_once()


# --------------------------------------------------------------------------
# 5.4: Integration test - parallel mode with conflict detection and reporting
# --------------------------------------------------------------------------


class TestParallelConflictDetection:
    @patch("veridical.orchestrator.loop.detect_gtr", return_value=True)
    @patch.object(ParallelDispatcher, "dispatch")
    @patch.object(ConflictResolver, "merge_branches")
    def test_conflict_reported(
        self,
        mock_merge: MagicMock,
        mock_dispatch: AsyncMock,
        parallel_config: VeridicalConfig,
        tmp_path: Path,
    ) -> None:
        subtasks = [
            Subtask(id="task-1", description="Fix auth"),
            Subtask(id="task-2", description="Fix auth v2"),
        ]

        mock_dispatch.return_value = DispatchResult(
            worker_results=[
                WorkerResult(
                    subtask=subtasks[0], branch="veri/task-1", result=_make_success_result()
                ),
                WorkerResult(
                    subtask=subtasks[1], branch="veri/task-2", result=_make_success_result()
                ),
            ]
        )

        # Second merge has a conflict
        mock_merge.return_value = MergeResult(
            outcomes=[
                MergeOutcome(branch="veri/task-1", success=True),
                MergeOutcome(branch="veri/task-2", success=False, error="conflict"),
            ]
        )

        loop = OrchestratorLoop(parallel_config, tmp_path, max_workers=2)
        result = asyncio.run(loop.run("Fix auth", subtasks=subtasks))

        assert result.success is False
        assert result.merge is not None
        assert result.merge.conflicted_branches == ["veri/task-2"]
        assert result.error == "Some branches had merge conflicts."


# --------------------------------------------------------------------------
# 5.5: Integration test - final integrated verification runs after merge
# --------------------------------------------------------------------------


class TestFinalVerificationAfterMerge:
    @patch("veridical.orchestrator.loop.detect_gtr", return_value=True)
    @patch("veridical.orchestrator.loop.Verifier")
    @patch.object(ParallelDispatcher, "dispatch")
    @patch.object(ConflictResolver, "merge_branches")
    def test_verification_runs_and_fails(
        self,
        mock_merge: MagicMock,
        mock_dispatch: AsyncMock,
        mock_verifier_cls: MagicMock,
        parallel_config: VeridicalConfig,
        tmp_path: Path,
    ) -> None:
        subtasks = [Subtask(id="task-1", description="Add feature")]

        mock_dispatch.return_value = DispatchResult(
            worker_results=[
                WorkerResult(
                    subtask=subtasks[0], branch="veri/task-1", result=_make_success_result()
                ),
            ]
        )

        mock_merge.return_value = MergeResult(
            outcomes=[
                MergeOutcome(branch="veri/task-1", success=True),
            ]
        )

        # Final verification FAILS
        mock_verifier = MagicMock()
        mock_verifier.run_all = AsyncMock(
            return_value=VerificationResult(
                passed=False,
                gates=[
                    GateResult(
                        name="test-gate",
                        status=GateStatus.FAILED,
                        severity=GateSeverity.FAIL,
                        duration_seconds=0.1,
                    )
                ],
                duration_seconds=0.1,
            )
        )
        mock_verifier_cls.return_value = mock_verifier

        loop = OrchestratorLoop(parallel_config, tmp_path, max_workers=2)
        result = asyncio.run(loop.run("Add feature", subtasks=subtasks))

        assert result.success is False
        assert result.verification_passed is False
        assert result.merge is not None
        assert result.merge.all_merged is True


# --------------------------------------------------------------------------
# 5.6: Integration test - veri parallel --dry-run shows decomposition plan
# --------------------------------------------------------------------------


class TestDryRunDecomposition:
    def test_dry_run_decomposes_without_executing(self) -> None:
        """Verify that TaskDecomposer produces a plan without needing
        any supervisor or gtr infrastructure."""
        decomposer = TaskDecomposer()
        task = "1. Add login page\n2. Add signup page\n3. Add dashboard"
        subtasks = decomposer.decompose(task)

        assert len(subtasks) == 3
        assert subtasks[0].id == "task-1"
        assert subtasks[1].id == "task-2"
        assert subtasks[2].id == "task-3"
        # In dry-run mode the CLI would display these and exit;
        # the decomposer itself is the testable unit here.

    def test_dry_run_from_tasks_file(self, tmp_path: Path) -> None:
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text(
            "## 1. Work\n- [ ] 1.1 Create module\n- [ ] 1.2 Add tests\n- [x] 1.3 Done already\n"
        )
        decomposer = TaskDecomposer()
        subtasks = decomposer.decompose_from_tasks_file(tasks_file)

        assert len(subtasks) == 2
        assert "Create module" in subtasks[0].description
        assert "Add tests" in subtasks[1].description


# --------------------------------------------------------------------------
# Additional: gtr not installed → error
# --------------------------------------------------------------------------


class TestGtrRequired:
    @patch("veridical.orchestrator.loop.detect_gtr", return_value=False)
    def test_gtr_missing_returns_error(
        self,
        parallel_config: VeridicalConfig,
        tmp_path: Path,
    ) -> None:
        loop = OrchestratorLoop(parallel_config, tmp_path)
        result = asyncio.run(loop.run("Some task"))

        assert result.success is False
        assert result.error is not None
        assert "gtr" in result.error.lower()


# --------------------------------------------------------------------------
# Additional: all workers fail → no merge attempted
# --------------------------------------------------------------------------


class TestAllWorkersFail:
    @patch("veridical.orchestrator.loop.detect_gtr", return_value=True)
    @patch.object(ParallelDispatcher, "dispatch")
    def test_no_merge_when_all_fail(
        self,
        mock_dispatch: AsyncMock,
        parallel_config: VeridicalConfig,
        tmp_path: Path,
    ) -> None:
        subtasks = [Subtask(id="task-1", description="Fail")]

        mock_dispatch.return_value = DispatchResult(
            worker_results=[
                WorkerResult(
                    subtask=subtasks[0], branch="veri/task-1", result=_make_failure_result()
                ),
            ]
        )

        loop = OrchestratorLoop(parallel_config, tmp_path)
        result = asyncio.run(loop.run("Fail", subtasks=subtasks))

        assert result.success is False
        assert result.merge is None
        assert result.error == "All workers failed."
