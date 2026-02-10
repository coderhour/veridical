"""Local command - runs the verify-and-fix loop locally."""

import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from veridical.cli.spec_selector import select_spec
from veridical.config.loader import load_config
from veridical.exceptions import VeridicalError
from veridical.local.providers.registry import LocalProviderRegistry
from veridical.local.supervisor import LocalSupervisor
from veridical.logging_config import setup_logging
from veridical.openspec import find_open_specs, match_spec_from_description

if TYPE_CHECKING:
    from veridical.local.providers.protocol import LocalProvider

logger = logging.getLogger(__name__)
console = Console()


def _resolve_provider(
    provider_name: str | None,
    config_provider: str | None,
    worker_command: str | None,
) -> "LocalProvider | None":
    """Resolve a local provider from CLI flag, config, or auto-detection.

    Args:
        provider_name: Provider name from --provider flag
        config_provider: Provider name from config.local.provider
        worker_command: Worker command from --worker flag

    Returns:
        Resolved LocalProvider instance, or None if using raw worker command
    """
    # CLI --provider flag takes highest precedence
    name = provider_name or config_provider

    if name:
        try:
            provider_cls = LocalProviderRegistry.resolve(name)
            provider = provider_cls()
            console.print(f"[dim]Using provider: {provider.description}[/dim]")
            return provider
        except KeyError as e:
            available = ", ".join(LocalProviderRegistry.available()) or "(none)"
            console.print(f"[bold red]Error:[/bold red] {e}\nAvailable providers: {available}")
            raise typer.Exit(code=1) from e

    # If no explicit provider and no worker command, try auto-detection
    if not worker_command:
        detected = [info for info in LocalProviderRegistry.detect_available() if info.detected]
        if len(detected) == 1:
            provider_cls = LocalProviderRegistry.resolve(detected[0].name)
            provider = provider_cls()
            console.print(f"[dim]Auto-detected provider: {provider.description}[/dim]")
            return provider
        elif len(detected) > 1:
            console.print("[bold]Multiple providers detected. Select one:[/bold]")
            for i, info in enumerate(detected, 1):
                console.print(f"  {i}. {info.name} - {info.description}")
            try:
                choice = int(input("Select provider [1]: ").strip() or "1")
                if 1 <= choice <= len(detected):
                    provider_cls = LocalProviderRegistry.resolve(detected[choice - 1].name)
                    provider = provider_cls()
                    console.print(f"[dim]Using provider: {provider.description}[/dim]")
                    return provider
            except (ValueError, KeyboardInterrupt):
                console.print("[yellow]Aborted[/yellow]")
                raise typer.Exit(code=0) from None

    return None


def _list_providers() -> None:
    """Display a table of available providers with detection status."""
    providers = LocalProviderRegistry.detect_available()
    if not providers:
        console.print("[dim]No providers registered.[/dim]")
        return

    table = Table(title="Available Local Providers")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Detected", justify="center")

    for info in providers:
        status = "[green]\u2713[/green]" if info.detected else "[red]\u2717[/red]"
        table.add_row(info.name, info.description, status)

    console.print(table)


def run_local_supervisor(
    task: str,
    worker_command: str | None,
    max_iterations: int | None,
    dry_run: bool,
    config_path: Path | None,
    verbose: bool,
    tasks_file: Path | None = None,
    provider_name: str | None = None,
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

        # Resolve provider
        provider = _resolve_provider(
            provider_name, config.local.provider, worker_command or config.local.worker_command
        )

        async def _run() -> None:
            # Initialize Supervisor
            supervisor = LocalSupervisor(
                config, Path.cwd(), verbose=verbose, console=console, provider=provider
            )

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

            console.print(Panel(content, title=f"[{style}]{title}[/{style}]", border_style=style))

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
    provider: Annotated[
        str | None,
        typer.Option(
            "--provider",
            "-p",
            help="Named local provider preset (e.g., 'claude-code', 'gemini-cli')",
        ),
    ] = None,
    list_providers: Annotated[
        bool,
        typer.Option(
            "--list-providers",
            help="List available providers with detection status and exit",
        ),
    ] = False,
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
    no_spec: Annotated[
        bool,
        typer.Option(
            "--no-spec",
            "--skip-tasks",
            help="Skip OpenSpec task verification",
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
        veridical local
        veridical local "Fix bug" --provider claude-code
        veridical local "Fix bug" --provider gemini-cli
        veridical local "Fix bug" --worker "./agent.py fix"
        veridical local --list-providers
        veridical local "Fix bug" --no-spec
    """
    if list_providers:
        _list_providers()
        raise typer.Exit(code=0)

    if dry_run:
        console.print("[yellow]Dry run mode - commands will not be executed[/yellow]")

    if max_iterations:
        console.print(f"[dim]Max iterations: {max_iterations}[/dim]")

    # Spec detection and selection (mirrors veri run behavior)
    if not no_spec and not tasks_file:
        open_specs = find_open_specs()
        matched_spec = None

        if task:
            matched_spec = match_spec_from_description(task, open_specs)

        if not matched_spec and open_specs:
            matched_spec = select_spec(open_specs)

        if matched_spec:
            tasks_file = matched_spec.tasks_file
            if not task:
                task = f"Implement spec {matched_spec.name}"
                console.print(f"[bold blue]Auto-generated task:[/bold blue] {task}")
            console.print(f"[bold blue]Tracking tasks in:[/bold blue] {tasks_file}")

    # If still no task, prompt the user
    if not task:
        task = typer.prompt("What should the agent do?", default="").strip()
        if not task:
            console.print("[bold red]Error:[/bold red] No task description provided.")
            raise typer.Exit(code=1)

    run_local_supervisor(
        task,
        worker_command,
        max_iterations,
        dry_run,
        config_path,
        verbose,
        tasks_file=tasks_file,
        provider_name=provider,
    )
