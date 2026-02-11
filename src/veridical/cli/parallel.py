"""Parallel command - orchestrates multiple concurrent workers."""

import asyncio
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from veridical.config.loader import load_config
from veridical.exceptions import VeridicalError
from veridical.local.gtr import GTR_INSTALL_URL, detect_gtr
from veridical.openspec import find_open_specs
from veridical.orchestrator.decomposer import Subtask, TaskDecomposer
from veridical.orchestrator.loop import OrchestratorLoop

logger = logging.getLogger(__name__)
console = Console()


def parallel(
    task: Annotated[
        str | None,
        typer.Argument(
            help="Task description to decompose and run in parallel",
        ),
    ] = None,
    max_workers: Annotated[
        int | None,
        typer.Option(
            "--max-workers",
            "-w",
            help="Maximum number of concurrent workers (overrides config)",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show decomposition plan without executing",
        ),
    ] = False,
    tasks_file: Annotated[
        Path | None,
        typer.Option(
            "--tasks-file",
            "-f",
            help="Path to a tasks.md file to decompose",
        ),
    ] = None,
    task_list_file: Annotated[
        Path | None,
        typer.Option(
            "--task-list",
            help="Path to a plain-text file with one task per line",
        ),
    ] = None,
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to configuration file",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output",
        ),
    ] = False,
) -> None:
    """Run multiple workers in parallel on decomposed subtasks.

    Decomposes a task into independent subtasks and dispatches each to
    its own LocalSupervisor instance running in an isolated gtr worktree.
    After all workers complete, branches are merged sequentially and a
    final integrated verification is run.

    Requires gtr (Git Worktree Runner) to be installed.

    Examples:
        veri parallel "1. Add login page  2. Add signup page"
        veri parallel --tasks-file openspec/changes/my-change/tasks.md
        veri parallel --dry-run "Fix auth; Fix payments; Fix notifications"
    """
    # Pre-flight: gtr required
    if not detect_gtr():
        console.print(
            f"[bold red]Error:[/bold red] gtr (Git Worktree Runner) is required "
            f"for parallel mode.\nInstall it from: {GTR_INSTALL_URL}"
        )
        raise typer.Exit(code=1)

    try:
        config = load_config(config_path)
        if verbose:
            config.log_level = "DEBUG"
    except VeridicalError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e

    effective_workers = max_workers or config.parallel.max_workers

    # Resolve subtasks from the various input modes
    subtasks: list[Subtask] | None = None
    decomposer = TaskDecomposer()

    if task_list_file:
        # Plain text file: one task per line
        if not task_list_file.exists():
            console.print(f"[bold red]Error:[/bold red] File not found: {task_list_file}")
            raise typer.Exit(code=1)
        lines = [
            ln.strip()
            for ln in task_list_file.read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        subtasks = [Subtask(id=f"task-{i}", description=ln) for i, ln in enumerate(lines, 1)]
    elif tasks_file:
        # OpenSpec tasks.md
        if not tasks_file.exists():
            console.print(f"[bold red]Error:[/bold red] File not found: {tasks_file}")
            raise typer.Exit(code=1)
        subtasks = decomposer.decompose_from_tasks_file(tasks_file)
    elif task:
        subtasks = decomposer.decompose(task)
    else:
        # Try to read open OpenSpec changes
        open_specs = find_open_specs()
        if open_specs:
            console.print(f"[bold blue]Found {len(open_specs)} open OpenSpec change(s)[/bold blue]")
            subtasks = [
                Subtask(
                    id=f"spec-{i}",
                    description=f"Implement spec {spec.name}",
                )
                for i, spec in enumerate(open_specs, 1)
            ]
        else:
            console.print(
                "[bold red]Error:[/bold red] No task provided. "
                "Pass a task string, --tasks-file, --task-list, or have open OpenSpec changes."
            )
            raise typer.Exit(code=1)

    if not subtasks:
        console.print("[bold red]Error:[/bold red] No subtasks could be derived from input.")
        raise typer.Exit(code=1)

    # Dry run: show decomposition and exit
    if dry_run:
        table = Table(title="Decomposition Plan (dry run)")
        table.add_column("ID", style="cyan")
        table.add_column("Description")
        for st in subtasks:
            table.add_row(st.id, st.description)
        console.print(table)
        console.print(
            f"\n[dim]Would dispatch {len(subtasks)} worker(s) "
            f"(max {effective_workers} concurrent)[/dim]"
        )
        raise typer.Exit(code=0)

    # Run the orchestration loop
    task_desc = task or "parallel orchestration"

    try:

        async def _run() -> None:
            loop = OrchestratorLoop(
                config,
                Path.cwd(),
                max_workers=max_workers,
                console=console,
            )
            result = await loop.run(task_desc, subtasks=subtasks)

            # Summary panel
            style = "green" if result.success else "red"
            title = "PARALLEL COMPLETE" if result.success else "PARALLEL FAILED"

            lines = [
                f"[bold]Subtasks:[/bold] {len(result.subtasks)}",
                f"[bold]Succeeded:[/bold] {len(result.dispatch.succeeded)}",
                f"[bold]Failed:[/bold] {len(result.dispatch.failed)}",
            ]
            if result.merge:
                lines.append(f"[bold]Merged:[/bold] {len(result.merge.merged_branches)}")
                if result.merge.conflicted_branches:
                    lines.append(
                        f"[bold]Conflicts:[/bold] {', '.join(result.merge.conflicted_branches)}"
                    )
            if result.verification_passed is not None:
                v_status = (
                    "[green]passed[/green]" if result.verification_passed else "[red]failed[/red]"
                )
                lines.append(f"[bold]Final verification:[/bold] {v_status}")
            if result.error:
                lines.append(f"[bold]Error:[/bold] {result.error}")

            console.print(
                Panel(
                    "\n".join(lines),
                    title=f"[{style}]{title}[/{style}]",
                    border_style=style,
                )
            )

            if not result.success:
                raise typer.Exit(code=1)

        asyncio.run(_run())

    except VeridicalError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e
