"""Resume command."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from veridical.openspec import find_open_specs, match_spec_from_description
from veridical.supervisor.state import LoopState

console = Console()


def resume(
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Simulate without making API calls",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output",
        ),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to configuration file",
        ),
    ] = None,
) -> None:
    """Resume a previously interrupted Veridical session."""
    state_file = Path.cwd() / ".veridical_state.json"

    if not state_file.exists():
        console.print("[bold red]Error:[/bold red] No saved state found in current directory.")
        console.print("[dim]Use 'veridical run' to start a new session.[/dim]")
        raise typer.Exit(code=1)

    try:
        # Load state header to display info
        state = LoopState.load(state_file)
        console.print("[bold green]Found saved state![/bold green]")
        console.print(f"Task: {state.task_description}")
        console.print(f"Session: {state.session_id}")
        console.print(f"Iteration: {state.iteration}")

        # Attempt to re-detect spec
        tasks_file = None
        # We catch exceptions here to avoid failing resume if spec detection fails
        try:
            open_specs = find_open_specs()
            matched_spec = match_spec_from_description(state.task_description, open_specs)
            if matched_spec:
                tasks_file = matched_spec.tasks_file
                console.print(f"[bold blue]Tracking tasks in:[/bold blue] {tasks_file}")
        except Exception as e:
            console.print(f"[dim]Warning: Could not auto-detect spec: {e}[/dim]")

        # Run supervisor
        # Run supervisor
        from veridical.cli.run import run_supervisor

        run_supervisor(
            task=state.task_description,
            max_iterations=None,  # Resume indefinitely until done or user limit
            dry_run=dry_run,
            config_path=config_path,
            session_id=None,  # session_id is loaded from state
            verbose=verbose,
            tasks_file=tasks_file,
            target_branch=None,  # loaded from state
            resume_from_state=True,
        )

    except Exception as e:
        console.print(f"[bold red]Error resuming session:[/bold red] {e}")
        raise typer.Exit(code=1) from e
