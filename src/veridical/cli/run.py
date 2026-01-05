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
from veridical.cli.spec_selector import select_spec
from veridical.config.loader import load_config
from veridical.exceptions import VeridicalError
from veridical.openspec import find_open_specs, match_spec_from_description
from veridical.supervisor.loop import Supervisor

logger = logging.getLogger(__name__)

console = Console()


def run_supervisor(
    task: str,
    max_iterations: int | None,
    dry_run: bool,
    config_path: Path | None,
    session_id: str | None,
    tasks_file: Path | None = None,
    target_branch: str | None = None,
) -> None:
    """Async wrapper for running the supervisor."""
    try:
        # Load configuration
        config = load_config(config_path)

        if max_iterations:
            config.supervisor.max_iterations = max_iterations

        # Re-configure logging based on config file
        from veridical.logging_config import setup_logging

        setup_logging(
            level=config.log_level, verbose=os.environ.get("VERIDICAL_VERBOSE") == "true" or False
        )

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

                if session_id:
                    logger.info(f"Resuming session {session_id} for task: {task}")
                else:
                    logger.info(f"Starting supervisor loop for task: {task}")

                # Run loop
                result = await supervisor.run(
                    task, session_id=session_id, tasks_file=tasks_file, target_branch=target_branch
                )

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

                if result.target_branch:
                    content += f"[bold]Target Branch:[/bold] {result.target_branch}\n"

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
                "[yellow]Dry run: Options parsed successfully. Supervisor not started.[/yellow]"
            )
            if tasks_file:
                console.print(f"[dim]Detected tasks file: {tasks_file}[/dim]")
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


def run(
    task: Annotated[
        str | None,
        typer.Argument(
            help="Description of the task to perform",
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
    session_id: Annotated[
        str | None,
        typer.Option(
            "--session-id",
            "-s",
            help="Resume an existing Jules session instead of creating a new one",
        ),
    ] = None,
    no_spec: Annotated[
        bool,
        typer.Option(
            "--no-spec",
            "--skip-tasks",
            help="Skip OpenSpec task verification",
        ),
    ] = False,
    target_branch: Annotated[
        str | None,
        typer.Option(
            "--target-branch",
            "-b",
            help="Override the target branch for merging changes",
        ),
    ] = None,
) -> None:
    """Start an autonomous task loop with Jules.

    The supervisor will:
    1. Dispatch the task to Jules (or resume existing session with --session-id)
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
        veridical run "Continue the task" --session-id abc123
        veridical run "Continue the task" -s abc123
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

    if max_iterations:
        console.print(f"[dim]Max iterations: {max_iterations}[/dim]")

    # Dynamic spec detection
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

    if session_id:
        console.print(f"[bold]Resuming session:[/bold] {session_id}")
        console.print(f"[bold]Task:[/bold] {task}")
    else:
        console.print(f"[bold]Starting autonomous task:[/bold] {task}")

    run_supervisor(
        task,
        max_iterations,
        dry_run,
        config_path,
        session_id,
        tasks_file=tasks_file,
        target_branch=target_branch,
    )
