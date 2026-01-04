"""Config command - configuration management."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.syntax import Syntax

from veridical.config.defaults import get_config_template
from veridical.config.loader import generate_config_template, load_config
from veridical.exceptions import ConfigurationError

console = Console()

config_app = typer.Typer(
    name="config",
    help="Manage Veridical configuration",
    no_args_is_help=True,
)


@config_app.command("show")
def config_show(
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to configuration file",
        ),
    ] = None,
) -> None:
    """Display current effective configuration.

    Shows the merged configuration from defaults, config file,
    and environment variables.
    """
    try:
        config = load_config(config_path)
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(code=1) from None

    console.print("[bold]Effective Configuration[/bold]\n")

    # Display as formatted JSON
    import json

    config_dict = config.model_dump()
    config_json = json.dumps(config_dict, indent=2, default=str)

    syntax = Syntax(config_json, "json", theme="monokai", line_numbers=True)
    console.print(syntax)


@config_app.command("init")
def config_init(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output path for config file",
        ),
    ] = Path(".veridical.yaml"),
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Overwrite existing file",
        ),
    ] = False,
    template: Annotated[
        str,
        typer.Option(
            "--template",
            "-t",
            help="Name of the template to use (e.g., python)",
        ),
    ] = "python",
) -> None:
    """Create a configuration template file.

    Generates a .veridical.yaml file with documented options
    and sensible defaults.
    """
    try:
        path = generate_config_template(output, force=force, template=template)
        console.print(f"[green]Created configuration file: {path}[/green]")
        console.print("[dim]Edit this file to customize your settings.[/dim]")
    except ConfigurationError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from None


@config_app.command("template")
def config_template(
    template: Annotated[
        str,
        typer.Option(
            "--template",
            "-t",
            help="Name of the template to use (e.g., python)",
        ),
    ] = "python",
) -> None:
    """Print the configuration template to stdout.

    Useful for piping to a file or reviewing the format.
    """
    try:
        template_content = get_config_template(template)
        syntax = Syntax(template_content, "yaml", theme="monokai", line_numbers=True)
        console.print(syntax)
    except ConfigurationError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from None
