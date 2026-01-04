"""Run command - initiates the autonomous quality loop."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from veridical.api.client import JulesClient
from veridical.cli.git_utils import check_spec_status, format_spec_warning
from veridical.config.loader import load_config
from veridical.exceptions import VeridicalError
from veridical.supervisor.loop import Supervisor

logger = logging.getLogger(__name__)

console = Console()


def run_supervisor(
    task: str,
    max_iterations: int | None,
    dry_run: bool,
    config_path: Path | None,
) -> None:
    """Async wrapper for running the supervisor."""
    try:
        # Load configuration
        config = load_config(config_path)

        # Override config with CLI options
        if max_iterations:
            config.supervisor.max_iterations = max_iterations

        # Get API key
        api_key = os.environ.get("JULES_API_KEY")
        if not api_key:
            if dry_run:
                api_key = "dummy_key"
            else:
                console.print(
                    "[bold red]Error:[/bold red] JULES_API_KEY environment variable not set."
                )
                raise typer.Exit(code=1)

        async def _run() -> None:
            async with JulesClient(
                api_key=api_key,
                base_url=config.jules.api_base_url,
                timeout=config.jules.poll_timeout,
            ) as client:
                # Initialize Supervisor
                supervisor = Supervisor(config, client, Path.cwd())

                if dry_run:
                    console.print(
                        "[yellow]Dry run: Initialized supervisor but not running loop[/yellow]"
                    )
                    return

                logger.info(f"Starting supervisor loop for task: {task}")

                # Run loop
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
                if result.final_commit:
                    content += f"[bold]Final Commit:[/bold] {result.final_commit}\n"

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


def run(
    task: Annotated[
        str,
        typer.Argument(
            help="Description of the task to perform",
        ),
    ],
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
            help="Simulate without making API calls",
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
    """Start an autonomous task loop with Jules.

    The supervisor will:
    1. Dispatch the task to Jules
    2. Poll for completion
    3. Sync patches locally
    4. Run quality gates
    5. Loop until success or max iterations

    Works for any task: bug fixes, new features, refactoring, documentation, etc.

    Examples:
        veridical run "Fix the login validation bug"
        veridical run "Add user profile page with avatar upload"
        veridical run "Refactor the authentication module"
        veridical run "Add comprehensive tests for the API client"
    """
    if dry_run:
        console.print("[yellow]Dry run mode - no API calls will be made[/yellow]")

    # Check for unpushed spec changes
    spec_status = check_spec_status()
    if spec_status.needs_attention:
        console.print()
        console.print(format_spec_warning(spec_status))
        console.print()
        if not typer.confirm("Do you want to continue anyway?", default=False):
            console.print("[yellow]Aborted. Push your changes first with: git push[/yellow]")
            raise typer.Exit(code=0)

    console.print(f"[bold]Starting autonomous task:[/bold] {task}")

    if max_iterations:
        console.print(f"[dim]Max iterations: {max_iterations}[/dim]")

    run_supervisor(task, max_iterations, dry_run, config_path)
