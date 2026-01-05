import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from veridical.openspec.scanner import OpenSpecInfo

console = Console()


def select_spec(specs: list[OpenSpecInfo]) -> OpenSpecInfo | None:
    """
    Shows interactive spec selector and returns selected spec.
    """
    if not specs:
        return None

    table = Table(show_header=True, header_style="bold blue")
    table.add_column("#", style="dim", width=4)
    table.add_column("OpenSpec Change", style="cyan")
    table.add_column("Incomplete Tasks", justify="right")

    for i, spec in enumerate(specs, 1):
        status = f"{spec.incomplete_count} of {spec.total_count}"
        table.add_row(str(i), spec.name, status)

    table.add_row("0", "None / Bug Fix", "-", style="dim")

    console.print(
        Panel(
            table,
            title="[bold]Select OpenSpec Change[/bold]",
            subtitle="[dim]Choose a spec to track task completion[/dim]",
            border_style="blue",
        )
    )

    while True:
        choice = typer.prompt(
            f"Select spec [0-{len(specs)}]",
            default="0",
        )

        try:
            val = int(choice)
            if val == 0:
                return None
            if 1 <= val <= len(specs):
                return specs[val - 1]
        except ValueError:
            pass

        console.print("[red]Invalid selection. Please try again.[/red]")
