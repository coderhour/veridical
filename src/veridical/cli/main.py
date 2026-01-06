"""Main CLI application using Typer."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from veridical import __version__
import anyio
from veridical.cli.config import config_app
from veridical.cli.resume import resume
from veridical.cli.run import run
from veridical.cli.status import status
from veridical.cli.verify import verify
from veridical.logging_config import setup_logging

# Create main app
app = typer.Typer(
    name="veridical",
    help="Local Supervisory Control System for Google Jules",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Add subcommands
@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """
    Async Typer callback.
    """
    if ctx.invoked_subcommand is None:
        # No subcommand was invoked.
        pass

app.command(name="run")(run)
app.command(name="resume")(resume)
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
    version: Annotated[  # noqa: ARG001
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
    log_file: Annotated[
        Path | None,
        typer.Option(
            "--log-file",
            help="Path to save logs",
        ),
    ] = None,
) -> None:
    """Veridical - Autonomous quality assurance for Google Jules.

    Run quality gates locally or dispatch tasks to Jules with
    iterative verification loops.
    """
    setup_logging(log_file=log_file, verbose=verbose)


if __name__ == "__main__":
    app()
