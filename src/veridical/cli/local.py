"""Local command - runs the verify-and-fix loop locally."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from veridical.config.loader import load_config
from veridical.exceptions import VeridicalError
from veridical.local.supervisor import LocalSupervisor
from veridical.logging_config import setup_logging

logger = logging.getLogger(__name__)
console = Console()


def run_local_supervisor(
    task: str,
    worker_command: str | None,
    max_iterations: int | None,
    dry_run: bool,
    config_path: Path | None,
    verbose: bool,
    tasks_file: Path | None = None,
) -> None:
    """Async wrapper for running the local supervisor."""
    try:
        # Load configuration
        config = load_config(config_path)

        if max_iterations:
            config.supervisor.max_iterations = max_iterations

        if worker_command:
            config.local.worker_command = worker_command

        # Re-configure logging based on config file
        setup_logging(
            level=config.log_level, verbose=os.environ.get("VERIDICAL_VERBOSE") == "true" or False
        )

        async def _run() -> None:
            # Initialize Supervisor
            supervisor = LocalSupervisor(config, Path.cwd(), verbose=verbose, console=console)

            logger.info(f"Starting local supervisor loop for task: {task}")

            # Run loop
            result = await supervisor.run(task, tasks_file=tasks_file)

            # Report results
            style = "green" if result.success else "red"
            title = "SUCCESS" if result.success else "FAILED"

            content = f"""
[bold]Iterations:[/bold] {result.iterations}
[bold]Duration:[/bold] {result.duration_seconds:.2f}s
[bold]Started:[/bold] {result.started_at.isoformat()}
[bold]Completed:[/bold] {result.completed_at.isoformat()}
"""

            if result.failure_reason:
                content += f"\n[bold]Failure Reason:[/bold] {result.failure_reason}"

            if result.error_context and verbose:
                content += f"\n[bold]Error Context:[/bold]\n{result.error_context}"

            console.print(
                Panel(content, title=f"[{style}]{title}[/{style}]", border_style=style)
            )

            if not result.success:
                raise typer.Exit(code=1)

        if dry_run:
            console.print(
                "[yellow]Dry run: Options parsed successfully. Local supervisor not started.[/yellow]"
            )
            return

        asyncio.run(_run())

    except VeridicalError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if e.details:
            console.print(f"[dim]{e.details}[/dim]")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e


def local_mode(
    task: Annotated[
        str | None,
        typer.Argument(
            help="Description of the task to perform",
        ),
    ] = None,
    worker_command: Annotated[
        str | None,
        typer.Option(
            "--worker",
            "-w",
            help="Command to execute as the AI worker (overrides config)",
        ),
    ] = None,
    max_iterations: Annotated[
        int | None,
        typer.Option(
            "--max-iterations",
            "-n",
            help="Maximum number of iterations",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Simulate without executing commands",
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
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output",
        ),
    ] = False,
    tasks_file: Annotated[
        Path | None,
        typer.Option(
            "--tasks-file",
            help="Path to tasks.md file for verification",
        ),
    ] = None,
) -> None:
    """Run a local verify-and-fix loop.

    This command runs a local worker command (e.g., an agent script)
    iteratively against the quality gates. It feeds verification errors
    back to the worker via environment variables.

    Examples:
        veridical local "Fix bug" --worker "./agent.py fix"
        veridical local --worker "python worker.py"
    """
    if dry_run:
        console.print("[yellow]Dry run mode - commands will not be executed[/yellow]")

    if max_iterations:
        console.print(f"[dim]Max iterations: {max_iterations}[/dim]")

    if not task:
        task = "Local autonomous task"
        console.print(f"[dim]Task description: {task}[/dim]")

    run_local_supervisor(
        task,
        worker_command,
        max_iterations,
        dry_run,
        config_path,
        verbose,
        tasks_file=tasks_file,
    )
