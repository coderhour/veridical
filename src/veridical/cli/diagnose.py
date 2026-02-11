from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from veridical.diagnose import Localizer

app = typer.Typer(help="Root-cause localization tools")
console = Console()


@app.callback(invoke_without_command=True)
def diagnose(
    ctx: typer.Context,
    error: Annotated[str | None, typer.Option(help="Traceback text to analyze")] = None,
    file: Annotated[Path | None, typer.Option(help="Path to log file to analyze")] = None,
    test: Annotated[str | None, typer.Option(help="Test name (placeholder)")] = None,
):
    """Run root-cause localization on an error."""
    if ctx.invoked_subcommand is not None:
        return

    if not error and not file and not test:
        console.print(
            "[bold red]Error:[/bold red] Either --error, --file, or --test must be provided."
        )
        raise typer.Exit(1)

    content = error
    if file:
        if not file.exists():
            console.print(f"[bold red]Error:[/bold red] File {file} does not exist.")
            raise typer.Exit(1)
        content = file.read_text()
    elif test:
        with console.status(f"[bold green]Running test {test}..."):
            import subprocess

            # Try to find pytest in .venv or system path
            pytest_path = "pytest"
            if (Path.cwd() / ".venv/bin/pytest").exists():
                pytest_path = str(Path.cwd() / ".venv/bin/pytest")

            result = subprocess.run(
                [pytest_path, "-k", test, "--color=no"], capture_output=True, text=True
            )
            content = result.stdout + result.stderr

    if not content:
        console.print("[bold yellow]Warning:[/bold yellow] No content to analyze.")
        return

    # Load config to get repo path (default to current dir)
    repo_path = Path.cwd()
    localizer = Localizer(repo_path)

    with console.status("[bold green]Analyzing error..."):
        report = localizer.localize(content)

    if not report.entries:
        console.print("[bold yellow]No potential root causes identified.[/bold yellow]")
        return

    console.print(
        f"\\n[bold blue]Localization Report[/bold blue] (found {len(report.entries)} candidates)\\n"
    )

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("File", style="dim")
    table.add_column("Line", justify="right")
    table.add_column("Function")
    table.add_column("Confidence", justify="right")
    table.add_column("Reason")

    for entry in sorted(report.entries, key=lambda x: x.confidence, reverse=True):
        color = "green" if entry.confidence > 0.7 else "yellow" if entry.confidence > 0.4 else "red"
        table.add_row(
            entry.file,
            str(entry.line),
            entry.function,
            f"[{color}]{entry.confidence:.2%}[/{color}]",
            entry.reason,
        )

    console.print(table)
    console.print(f"\\n[bold green]Suggested focus:[/bold green] {report.to_feedback_string()}\\n")
