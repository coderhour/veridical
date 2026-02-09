"""Local loop command."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from veridical.cli.git_utils import check_spec_status, format_spec_warning
from veridical.cli.spec_selector import select_spec
from veridical.config.loader import load_config
from veridical.exceptions import VeridicalError
from veridical.local.supervisor import LocalSupervisor
from veridical.openspec import find_open_specs, match_spec_from_description

logger = logging.getLogger(__name__)

console = Console()


def run_local_supervisor(
    task: str,
    max_iterations: int | None,
    worker_command: str | None,
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
        from veridical.logging_config import setup_logging

        setup_logging(
            level=config.log_level,
            verbose=verbose or (os.environ.get("VERIDICAL_VERBOSE") == "true"),
        )

        # Verify worker command is set
        if not config.local.worker_command:
            console.print("[bold red]Error:[/bold red] No worker command specified.")
            console.print(
                "Please provide --worker or set local.worker_command in configuration."
            )
            raise typer.Exit(code=1)

        async def _run() -> None:
            supervisor = LocalSupervisor(
                config, Path.cwd(), verbose=verbose, console=console
            )

            logger.info(f"Starting local supervisor loop for task: {task}")
            logger.info(f"Worker command: {config.local.worker_command}")

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

            if result.error_context:
                content += f"\n[bold]Error Context:[/bold]\n{result.error_context}"

            console.print(
                Panel(content, title=f"[{style}]{title}[/{style}]", border_style=style)
            )

            if not result.success:
                raise typer.Exit(code=1)

        asyncio.run(_run())

    except VeridicalError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if e.details:
            console.print(f"[dim]{e.details}[/dim]")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e


def local(
    task: Annotated[
        str | None,
        typer.Argument(
            help="Description of the task to perform",
        ),
    ] = None,
    worker: Annotated[
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
            help="Enable verbose output, including activity stream",
        ),
    ] = False,
    no_spec: Annotated[
        bool,
        typer.Option(
            "--no-spec",
            "--skip-tasks",
            help="Skip OpenSpec task verification",
        ),
    ] = False,
) -> None:
    """Start a local autonomous verification loop.

    Executes a local command (worker) repeatedly, running quality gates
    in between. The worker receives error feedback from failed gates.

    Ideal for use with local AI coding tools like `aider`, `claude-code`,
    or custom scripts.
    """
    # Check for unpushed spec changes
    spec_status = check_spec_status()
    if spec_status.needs_attention:
        console.print()
        console.print(format_spec_warning(spec_status))
        console.print()
        if not typer.confirm("Do you want to continue anyway?", default=False):
            console.print(
                "[yellow]Aborted. Push your changes first with: git push[/yellow]"
            )
            raise typer.Exit(code=0)

    if max_iterations:
        console.print(f"[dim]Max iterations: {max_iterations}[/dim]")

    # Dynamic spec detection (copied from run.py)
    tasks_file: Path | None = None
    if not no_spec:
        open_specs = find_open_specs()
        matched_spec = None

        if task:
            matched_spec = match_spec_from_description(task, open_specs)

        if not matched_spec and open_specs:
            # Task not provided or didn't match, but specs exist
            matched_spec = select_spec(open_specs)

        if matched_spec:
            tasks_file = matched_spec.tasks_file
            if not task:
                task = f"Implement spec {matched_spec.name}"
                console.print(f"[bold blue]Auto-generated task:[/bold blue] {task}")
            console.print(f"[bold blue]Tracking tasks in:[/bold blue] {tasks_file}")

    if not task:
        console.print(
            "[bold red]Error:[/bold red] No task description provided and no spec selected."
        )
        raise typer.Exit(code=1)

    console.print(f"[bold]Starting local task:[/bold] {task}")

    run_local_supervisor(
        task,
        max_iterations,
        worker,
        config_path,
        verbose,
        tasks_file=tasks_file,
    )
