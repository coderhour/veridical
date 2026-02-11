"""Verify command - runs local quality gates."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from veridical.config.loader import load_config
from veridical.verifier.quality_gate import Verifier

console = Console()


def verify(
    gate: Annotated[
        str | None,
        typer.Argument(
            help="Specific gate to run (runs all if not specified)",
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
    no_fix: Annotated[
        bool,
        typer.Option(
            "--no-fix",
            help="Disable autofix for gates with fix_command (check-only mode)",
        ),
    ] = False,
) -> None:
    """Run quality gates locally.

    Executes configured quality gates (tests, linters, type checkers)
    and reports results. Exit code is 0 if all gates pass, 1 otherwise.

    Autofix is enabled by default: gates with a fix_command will
    automatically attempt to fix issues. Use --no-fix to disable.

    Example:
        veridical verify
        veridical verify pytest
        veridical verify --no-fix
    """
    # Load configuration
    try:
        config = load_config(config_path)
    except Exception as e:
        console.print(f"[red]Failed to load config: {e}[/red]")
        raise typer.Exit(code=1) from None

    repo_path = Path.cwd()
    verifier = Verifier(config, repo_path)
    if no_fix:
        verifier.autofix_enabled = False

    console.print("[bold]Running quality gates...[/bold]\n")

    # Run verification
    try:
        result = asyncio.run(verifier.run_gate(gate)) if gate else asyncio.run(verifier.run_all())
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from None

    # Display results table
    table = Table(title="Quality Gate Results")
    table.add_column("Gate", style="cyan")
    table.add_column("Status")
    table.add_column("Duration", justify="right")

    for gate_result in result.gates:
        status = "[green]PASSED[/green]" if gate_result.passed else "[red]FAILED[/red]"

        table.add_row(
            gate_result.name,
            status,
            f"{gate_result.duration_seconds:.2f}s",
        )

    console.print(table)
    console.print(f"\n[dim]Total time: {result.duration_seconds:.2f}s[/dim]")

    if result.passed:
        console.print("\n[bold green]All gates passed![/bold green]")
        raise typer.Exit(code=0)
    else:
        console.print("\n[bold red]Some gates failed.[/bold red]")

        # Show failure details
        for gate_result in result.failed_gates:
            console.print(f"\n[red]--- {gate_result.name} ---[/red]")
            if gate_result.error_output:
                console.print(gate_result.error_output[:500])
            elif gate_result.output:
                console.print(gate_result.output[:500])

        raise typer.Exit(code=1)
