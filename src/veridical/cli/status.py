"""Status command - displays active session information."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def status(
    session_id: Annotated[
        str | None,
        typer.Argument(
            help="Specific session ID to check",
        ),
    ] = None,
) -> None:
    """Display status of active Jules sessions.

    Shows a table of active sessions including their current state,
    iteration count, and duration.

    Example:
        veridical status
        veridical status abc123
    """
    console.print("[bold]Veridical Session Status[/bold]\n")

    if session_id:
        console.print(f"[dim]Checking session: {session_id}[/dim]")
        # In full implementation:
        # 1. Load session from local state file
        # 2. Poll Jules API for current status
        # 3. Display detailed status

        console.print("[yellow]No active sessions found.[/yellow]")
        console.print(
            "[dim]Note: Session tracking will be implemented in a subsequent proposal.[/dim]"
        )
    else:
        # Display table of all active sessions
        table = Table(title="Active Sessions")
        table.add_column("Session ID", style="cyan")
        table.add_column("Status")
        table.add_column("Iteration")
        table.add_column("Started")

        # Skeleton - no sessions to show
        console.print("[yellow]No active sessions.[/yellow]")
        console.print("[dim]Use 'veridical fix <task>' to start a new session.[/dim]")

    raise typer.Exit(code=0)
