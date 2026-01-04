"""Default configuration values and templates."""

import importlib.resources as pkg_resources

from veridical.exceptions import ConfigurationError


def get_config_template(template: str = "python") -> str:
    """Return the default configuration template."""
    template_file = f"{template}.yaml.j2"
    try:
        # Use files() from importlib.resources to get a Traversable
        # Then joinpath() to specify the file and read_text() to get content
        return (
            pkg_resources.files("veridical.config.templates")
            .joinpath(template_file)
            .read_text()
        )
    except FileNotFoundError:
        raise ConfigurationError(
            f"Configuration template '{template}' not found.",
            details=f"Searched for '{template_file}' in templates.",
        ) from None
