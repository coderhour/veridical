"""Main CLI application using Typer."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from veridical import __version__
from veridical.cli.config import config_app
from veridical.cli.diagnose import diagnose
from veridical.cli.heal import heal
from veridical.cli.learn import learn_app
from veridical.cli.local import local_mode
from veridical.cli.report import report
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
app.command()(run)
app.command(name="local")(local_mode)
app.command()(heal)
app.command()(resume)
app.command()(verify)
app.command()(status)
app.command()(report)
app.command()(diagnose)
app.add_typer(config_app, name="config")
app.add_typer(learn_app, name="learn")

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
