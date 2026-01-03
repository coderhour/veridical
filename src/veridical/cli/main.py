"""Main CLI application using Typer."""

from typing import Annotated

import typer
from rich.console import Console

from veridical import __version__
from veridical.cli.config import config_app
from veridical.cli.run import run
from veridical.cli.status import status
from veridical.cli.verify import verify

# Create main app
app = typer.Typer(
    name="veridical",
    help="Local Supervisory Control System for Google Jules",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Add subcommands
app.command()(run)
app.command()(verify)
app.command()(status)
app.add_typer(config_app, name="config")

# Console for output
console = Console()


def version_callback(value: bool) -> None:
    """Display version and exit."""
    if value:
        console.print(f"veridical {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
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
    """Veridical - Autonomous quality assurance for Google Jules.

    Run quality gates locally or dispatch tasks to Jules with
    iterative verification loops.
    """
    # Store verbose flag in context for subcommands
    # Note: In a full implementation, we'd set up logging here
    pass


if __name__ == "__main__":
    app()
