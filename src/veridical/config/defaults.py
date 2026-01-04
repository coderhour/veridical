"""Default configuration values and templates."""

import importlib.resources as pkg_resources

from veridical.exceptions import ConfigurationError


def get_config_template(template: str = "python") -> str:
    """Return the default configuration template."""
    template_name = f"{template}.yaml"
    try:
        files = pkg_resources.files("veridical.config.templates")
        return (files / template_name).read_text()
    except (FileNotFoundError, NotADirectoryError) as e:
        raise ConfigurationError(
            f"Configuration template not found: {template}",
            details=f"No such file in templates directory: {template_name}",
        ) from e
