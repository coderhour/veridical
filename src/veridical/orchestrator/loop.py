"""Main orchestration loop: decompose -> dispatch -> monitor -> merge -> verify."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.console import Console

from veridical.local.gtr import detect_gtr
from veridical.orchestrator.decomposer import Subtask, TaskDecomposer
from veridical.orchestrator.dispatcher import DispatchResult, ParallelDispatcher
from veridical.orchestrator.resolver import ConflictResolver, MergeResult
from veridical.verifier.quality_gate import Verifier

if TYPE_CHECKING:
    from pathlib import Path

    from veridical.config.schema import VeridicalConfig

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationResult:
    """Final result of the parallel orchestration pipeline."""

    subtasks: list[Subtask]
    dispatch: DispatchResult
    merge: MergeResult | None
    verification_passed: bool | None
    error: str | None = None

    @property
    def success(self) -> bool:
        return (
            self.dispatch.all_succeeded
            and self.merge is not None
            and self.merge.all_merged
            and self.verification_passed is True
        )


class OrchestratorLoop:
    """Top-level orchestrator: decompose, dispatch, merge, verify.

    Coordinates the full parallel pipeline:
    1. Decompose the task into independent subtasks
    2. Dispatch each subtask to its own LocalSupervisor + gtr worktree
    3. Sequentially merge completed branches
    4. Run final integrated verification on the merged result
    """

    def __init__(
        self,
        config: VeridicalConfig,
        repo_path: Path,
        *,
        max_workers: int | None = None,
        console: Console | None = None,
    ) -> None:
        self.config = config
        self.repo_path = repo_path
        self.console = console or Console()
        self._decomposer = TaskDecomposer()
        self._dispatcher = ParallelDispatcher(
            config, repo_path, max_workers=max_workers, console=self.console
        )
        self._resolver = ConflictResolver(repo_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        task_description: str,
        *,
        subtasks: list[Subtask] | None = None,
        tasks_file: Path | None = None,
    ) -> OrchestrationResult:
        """Execute the full parallel orchestration pipeline.

        Args:
            task_description: High-level task description.
            subtasks: Pre-decomposed subtasks (skip decomposition).
            tasks_file: Optional tasks.md to decompose from.

        Returns:
            :class:`OrchestrationResult` with full pipeline outcome.
        """
        # 0. Pre-flight: gtr must be available
        if not detect_gtr():
            error = (
                "gtr (Git Worktree Runner) is required for parallel mode but was not found on PATH."
            )
            self.console.print(f"[bold red]Error:[/bold red] {error}")
            return OrchestrationResult(
                subtasks=[],
                dispatch=DispatchResult(),
                merge=None,
                verification_passed=None,
                error=error,
            )

        # 1. Decompose
        if subtasks is None:
            if tasks_file:
                subtasks = self._decomposer.decompose_from_tasks_file(tasks_file)
            else:
                subtasks = self._decomposer.decompose(task_description)

        if not subtasks:
            error = "Task decomposition produced no subtasks."
            self.console.print(f"[bold red]Error:[/bold red] {error}")
            return OrchestrationResult(
                subtasks=[],
                dispatch=DispatchResult(),
                merge=None,
                verification_passed=None,
                error=error,
            )

        self.console.print(f"[bold blue]Decomposed into {len(subtasks)} subtask(s)[/bold blue]")
        for st in subtasks:
            self.console.print(f"  [dim]{st.id}:[/dim] {st.description}")

        # 2. Dispatch
        self.console.print(
            f"\n[bold blue]Dispatching {len(subtasks)} workers "
            f"(max {self._dispatcher.max_workers} concurrent)[/bold blue]"
        )
        dispatch_result = await self._dispatcher.dispatch(subtasks)

        if dispatch_result.failed:
            self.console.print(
                f"[bold yellow]{len(dispatch_result.failed)} worker(s) failed[/bold yellow]"
            )
            for wr in dispatch_result.failed:
                self.console.print(
                    f"  [red]{wr.subtask.id}:[/red] {wr.result.failure_reason or 'unknown'}"
                )

        if not dispatch_result.succeeded:
            return OrchestrationResult(
                subtasks=subtasks,
                dispatch=dispatch_result,
                merge=None,
                verification_passed=None,
                error="All workers failed.",
            )

        # 3. Merge
        target_branch = self._get_current_branch()
        branches = dispatch_result.branches
        self.console.print(
            f"\n[bold blue]Merging {len(branches)} branch(es) into {target_branch}[/bold blue]"
        )
        merge_result = self._resolver.merge_branches(branches, target_branch)

        if merge_result.conflicted_branches:
            self.console.print("[bold yellow]Merge conflicts detected:[/bold yellow]")
            for b in merge_result.conflicted_branches:
                self.console.print(f"  [yellow]{b}[/yellow]")

        if not merge_result.all_merged:
            return OrchestrationResult(
                subtasks=subtasks,
                dispatch=dispatch_result,
                merge=merge_result,
                verification_passed=None,
                error="Some branches had merge conflicts.",
            )

        # 4. Final integrated verification
        self.console.print("\n[bold blue]Running final integrated verification[/bold blue]")
        verifier = Verifier(self.config, self.repo_path)
        verification = await verifier.run_all()

        if verification.passed:
            self.console.print("[bold green]Final verification passed![/bold green]")
        else:
            failed_names = ", ".join(verification.failed_gate_names)
            self.console.print(f"[bold red]Final verification failed:[/bold red] {failed_names}")

        # 5. Cleanup merged worktrees
        auto_cleanup = self.config.local.gtr_auto_cleanup
        self._resolver.cleanup_branches(merge_result.merged_branches, auto_cleanup=auto_cleanup)

        return OrchestrationResult(
            subtasks=subtasks,
            dispatch=dispatch_result,
            merge=merge_result,
            verification_passed=verification.passed,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_current_branch(self) -> str:
        """Detect the current branch in the main repo."""
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        branch = result.stdout.strip()
        if not branch or branch == "HEAD":
            return self.config.git.base_branch
        return branch
