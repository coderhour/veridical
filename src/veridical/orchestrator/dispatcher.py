"""Parallel dispatcher - spawns N concurrent LocalSupervisor instances."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console

from veridical.local.gtr import GtrWorktreeManager, generate_gtr_branch_name
from veridical.local.supervisor import LocalSupervisor

if TYPE_CHECKING:
    from pathlib import Path

    from veridical.config.schema import VeridicalConfig
    from veridical.models.result import LoopResult
    from veridical.orchestrator.decomposer import Subtask

logger = logging.getLogger(__name__)


@dataclass
class WorkerResult:
    """Result of a single parallel worker."""

    subtask: Subtask
    branch: str
    result: LoopResult


@dataclass
class DispatchResult:
    """Aggregated result from all parallel workers."""

    worker_results: list[WorkerResult] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        return all(wr.result.success for wr in self.worker_results)

    @property
    def succeeded(self) -> list[WorkerResult]:
        return [wr for wr in self.worker_results if wr.result.success]

    @property
    def failed(self) -> list[WorkerResult]:
        return [wr for wr in self.worker_results if not wr.result.success]

    @property
    def branches(self) -> list[str]:
        """Return branch names for successful workers."""
        return [wr.branch for wr in self.succeeded]


class ParallelDispatcher:
    """Dispatch subtasks to concurrent LocalSupervisor instances.

    Each worker runs in its own gtr worktree.  Concurrency is bounded
    by ``max_workers`` from :class:`ParallelConfig`.
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
        self.max_workers = max_workers or config.parallel.max_workers
        self.console = console or Console()
        self._gtr = GtrWorktreeManager(repo_path)

    async def dispatch(self, subtasks: list[Subtask]) -> DispatchResult:
        """Run *subtasks* in parallel, each in its own gtr worktree.

        Args:
            subtasks: Independent subtasks to execute concurrently.

        Returns:
            :class:`DispatchResult` with per-worker outcomes.
        """
        semaphore = asyncio.Semaphore(self.max_workers)
        result = DispatchResult()

        async def _run_worker(subtask: Subtask) -> WorkerResult:
            async with semaphore:
                branch = generate_gtr_branch_name(None, subtask.id)
                self.console.print(
                    f"[bold cyan]Worker {subtask.id}:[/bold cyan] starting on branch {branch}"
                )

                supervisor = LocalSupervisor(
                    self.config,
                    self.repo_path,
                    verbose=False,
                    console=self.console,
                    gtr_branch=branch,
                )

                loop_result = await supervisor.run(subtask.description)

                status = "[green]OK[/green]" if loop_result.success else "[red]FAIL[/red]"
                self.console.print(
                    f"[bold cyan]Worker {subtask.id}:[/bold cyan] {status} "
                    f"({loop_result.iterations} iterations)"
                )
                return WorkerResult(
                    subtask=subtask,
                    branch=branch,
                    result=loop_result,
                )

        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(_run_worker(st)) for st in subtasks]

        for task in tasks:
            result.worker_results.append(task.result())

        return result
