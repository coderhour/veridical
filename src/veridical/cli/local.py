"""Local command - initiates a local verification loop."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.console import Console
from rich.panel import Panel

from veridical.config.loader import load_config
from veridical.exceptions import VeridicalError
from veridical.local.supervisor import LocalSupervisor

logger = logging.getLogger(__name__)

console = Console()


def run_local_supervisor(
    task: str | None,
    worker_command: str | None,
    max_iterations: int | None,
    mode: Literal["interactive", "subprocess"] | None,
    dry_run: bool,
    config_path: Path | None,
    verbose: bool,
) -> None:
    """Async wrapper for running the local supervisor."""
    try:
        # Load configuration
        config = load_config(config_path)

        # Override config with CLI options
        if worker_command:
            config.local.worker_command = worker_command
        if max_iterations:
            config.supervisor.max_iterations = max_iterations
        if mode:
            config.local.mode = mode

        # Re-configure logging based on config file
        from veridical.logging_config import setup_logging

        setup_logging(
            level=config.log_level,
            verbose=verbose or os.environ.get("VERIDICAL_VERBOSE") == "true",
        )

        async def _run() -> None:
            supervisor = LocalSupervisor(config, Path.cwd(), verbose=verbose)

            result = await supervisor.run(task)

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

            if result.error_context:
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
            console.print(f"[dim]Worker Command: {config.local.worker_command}[/dim]")
            console.print(f"[dim]Mode: {config.local.mode}[/dim]")
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
            help="Description of the task to perform (optional)",
        ),
    ] = None,
    worker: Annotated[
        str | None,
        typer.Option(
            "--worker",
            "-w",
            help="Command to execute as the AI worker",
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
    mode: Annotated[
        str | None, # Typer doesn't handle Literal cleanly in all versions, string is safer
        typer.Option(
            "--mode",
            "-m",
            help="Execution mode (interactive/subprocess)",
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
) -> None:
    """Start a local verification loop.

    This mode runs a local command (the 'worker') and then verifies the results using
    configured quality gates. If verification fails, the error context is fed back
    to the worker in the next iteration.

    This is useful for:
    - Running local AI agents that can read error context from environment variables
    - Testing the verify-fix loop with a local script
    - Interactive debugging sessions
    """

    # Validate mode if provided
    valid_modes = ["interactive", "subprocess"]
    if mode and mode not in valid_modes:
        console.print(f"[bold red]Error:[/bold red] Invalid mode '{mode}'. Must be one of: {valid_modes}")
        raise typer.Exit(code=1)

    run_local_supervisor(
        task,
        worker,
        max_iterations,
        mode, # type: ignore
        dry_run,
        config_path,
        verbose,
    )
