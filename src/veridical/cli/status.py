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
    dashboard: Annotated[
        bool,
        typer.Option(
            "--dashboard",
            help="Show real-time dashboard of all active parallel sessions",
        ),
    ] = False,
) -> None:
    """Display status of active Jules sessions.

    Shows a table of active sessions including their current state,
    iteration count, and duration.

    Example:
        veridical status
        veridical status abc123
        veridical status --dashboard
    """
    if dashboard:
        _show_parallel_dashboard()
        raise typer.Exit(code=0)

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


def _show_parallel_dashboard() -> None:
    """Display a dashboard of active parallel worker sessions.

    Lists gtr worktrees with ``veri/`` prefix to show parallel workers
    that are currently running or have completed.
    """
    import subprocess

    console.print("[bold]Parallel Session Dashboard[/bold]\n")

    # List git worktrees to find active parallel sessions
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        console.print("[yellow]Could not list git worktrees.[/yellow]")
        return

    # Parse worktree list for veri/ branches
    worktrees: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1]
        elif line == "":
            if current:
                worktrees.append(current)
            current = {}
    if current:
        worktrees.append(current)

    parallel_workers = [
        wt
        for wt in worktrees
        if wt.get("branch", "").endswith("/") is False and "veri/" in wt.get("branch", "")
    ]

    if not parallel_workers:
        console.print("[yellow]No active parallel sessions.[/yellow]")
        console.print("[dim]Use 'veri parallel <task>' to start parallel workers.[/dim]")
        return

    table = Table(title="Parallel Workers")
    table.add_column("Branch", style="cyan")
    table.add_column("Worktree Path")

    for wt in parallel_workers:
        branch = wt.get("branch", "").replace("refs/heads/", "")
        table.add_row(branch, wt.get("path", ""))

    console.print(table)
