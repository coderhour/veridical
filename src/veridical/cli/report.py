"""Report command - generates structured summaries of completed runs."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from veridical.config.loader import load_config
from veridical.report.formatters import (
    TerminalFormatter,
    get_formatter,
)
from veridical.report.generator import ReportGenerator

console = Console()


def report(
    date: Annotated[
        str | None,
        typer.Option(
            "--date",
            "-d",
            help="Filter by date (YYYY-MM-DD)",
        ),
    ] = None,
    run_id: Annotated[
        str | None,
        typer.Option(
            "--run-id",
            "-r",
            help="Filter by session/run ID",
        ),
    ] = None,
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: terminal, json, html",
        ),
    ] = "",
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Write report to file instead of stdout",
        ),
    ] = None,
    list_runs: Annotated[
        bool,
        typer.Option(
            "--list",
            "-l",
            help="List available runs",
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
    """Generate structured summaries of completed runs.

    Summarizes work log data including per-iteration breakdown,
    aggregate metrics, cost tracking, and pattern insights.

    Examples:
        veridical report
        veridical report --date 2026-02-09
        veridical report --format json --output report.json
        veridical report --list
    """
    try:
        config = load_config(config_path)
    except Exception as e:
        console.print(f"[red]Failed to load config: {e}[/red]")
        raise typer.Exit(code=1) from None

    # Resolve format from config default if not specified
    if not format:
        format = config.report.default_format

    worklog_dir = Path.cwd() / config.worklog.directory
    generator = ReportGenerator(worklog_dir)

    # --list mode
    if list_runs:
        runs = generator.list_runs()
        if not runs:
            console.print("No runs found. Run `veri run` first to generate work logs.")
            raise typer.Exit(code=1)

        table = Table(title="Available Runs")
        table.add_column("Date", style="cyan")
        table.add_column("Session ID")
        table.add_column("Task")
        table.add_column("Outcome")
        table.add_column("Iterations", justify="right")

        for run in runs:
            outcome_style = "green" if run["outcome"] == "success" else "red"
            table.add_row(
                run["date"],
                run["session_id"],
                run["task_description"][:60],
                f"[{outcome_style}]{run['outcome']}[/{outcome_style}]",
                run["iterations"],
            )

        console.print(table)
        raise typer.Exit(code=0)

    # Generate report(s)
    if date or run_id:
        summaries = generator.generate(date=date, run_id=run_id)
    else:
        latest = generator.generate_latest()
        summaries = [latest] if latest else []

    if not summaries:
        console.print("No runs found. Run `veri run` first to generate work logs.")
        raise typer.Exit(code=1)

    formatter = get_formatter(format)

    for summary in summaries:
        if isinstance(formatter, TerminalFormatter):
            rendered = formatter.format(summary, console=console if output is None else None)
        else:
            rendered = formatter.format(summary)

        if output:
            output.write_text(rendered)
            console.print(f"[green]Report written to {output}[/green]")
        elif not isinstance(formatter, TerminalFormatter):
            # For json/html without --output, print to stdout
            console.print(rendered, highlight=False)
