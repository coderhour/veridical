"""Resume command - continues a previously interrupted loop."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from veridical.cli.run import run
from veridical.supervisor.state_model import STATE_FILE_NAME, LoopState

console = Console()


async def resume(
    config_path: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to configuration file"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-v", help="Enable verbose output, including activity stream"
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Simulate without making API calls"),
    ] = False,
) -> None:
    """Resume a previously interrupted Veridical loop."""
    state = LoopState.load(Path.cwd())

    if not state:
        console.print(
            f"[bold red]Error:[/bold red] No saved state file found at "
            f"{Path.cwd() / STATE_FILE_NAME}"
        )
        console.print("Cannot resume. Start a new loop with `veridical run`.")
        raise typer.Exit(code=1)

    console.print(
        Panel(
            f"[bold]Task:[/bold] {state.task_description}\n"
            f"[bold]Resuming at iteration:[/bold] {state.iteration}\n"
            f"[bold]Session ID:[/bold] {state.session_id or 'N/A'}",
            title="[yellow]Resuming Loop[/yellow]",
            border_style="yellow",
        )
    )

    tasks_file = Path(state.tasks_file) if state.tasks_file else None

    await run(
        task=state.task_description,
        max_iterations=None,
        dry_run=dry_run,
        config_path=config_path,
        session_id=state.session_id,
        verbose=verbose,
        tasks_file=tasks_file,
        target_branch=None,
        force_new=False,
    )
