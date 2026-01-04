"""Configuration loading utilities."""

from pathlib import Path
from typing import Any

import yaml

from veridical.config.defaults import ProjectType, get_config_template
from veridical.config.project_type import detect_project_type
from veridical.config.schema import VeridicalConfig
from veridical.exceptions import ConfigurationError

CONFIG_FILE_NAMES = [".veridical.yaml", ".veridical.yml"]


def find_config_file(start_dir: Path | None = None) -> Path | None:
    """Find the configuration file in the given directory or current directory.

    Args:
        start_dir: Directory to start searching from. Defaults to current directory.

    Returns:
        Path to the config file if found, None otherwise.
    """
    search_dir = start_dir or Path.cwd()

    for name in CONFIG_FILE_NAMES:
        config_path = search_dir / name
        if config_path.is_file():
            return config_path

    return None


def load_yaml_config(config_path: Path) -> dict[str, Any]:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Dictionary of configuration values.

    Raises:
        ConfigurationError: If the file cannot be read or parsed.
    """
    try:
        content = config_path.read_text()
        data = yaml.safe_load(content)
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Invalid YAML in configuration file: {config_path}",
            details=str(e),
        ) from e
    except OSError as e:
        raise ConfigurationError(
            f"Cannot read configuration file: {config_path}",
            details=str(e),
        ) from e


def load_config(
    config_path: Path | None = None,
    *,
    require_file: bool = False,
) -> VeridicalConfig:
    """Load Veridical configuration.

    Configuration is loaded from:
    1. Default values
    2. .veridical.yaml file (if present)
    3. Environment variables (prefixed with VERIDICAL_)

    Args:
        config_path: Explicit path to config file. If None, searches for config.
        require_file: If True, raise error if no config file found.

    Returns:
        Loaded and validated configuration.

    Raises:
        ConfigurationError: If configuration is invalid or required file missing.
    """
    # Find config file
    if config_path is None:
        config_path = find_config_file()

    if config_path is None and require_file:
        raise ConfigurationError(
            "Configuration file not found",
            details=f"Searched for: {', '.join(CONFIG_FILE_NAMES)}",
        )

    # Load file config if available
    file_config: dict[str, Any] = {}
    if config_path is not None:
        file_config = load_yaml_config(config_path)

    # Create config with file values, env vars will override
    try:
        config = VeridicalConfig(**file_config)
    except Exception as e:
        raise ConfigurationError(
            "Invalid configuration",
            details=str(e),
        ) from e

    return config


def generate_config_template(
    output_path: Path,
    *,
    force: bool = False,
    project_type: ProjectType | None = None,
) -> Path:
    """Generate a configuration template file.

    Args:
        output_path: Path to write the template to.
        force: If True, overwrite existing file.
        project_type: The type of project to generate a config for.

    Returns:
        Path to the generated file.

    Raises:
        ConfigurationError: If file exists and force is False, or if project
                            type cannot be determined.
    """
    if output_path.exists() and not force:
        raise ConfigurationError(
            f"Configuration file already exists: {output_path}",
            details="Use --force to overwrite",
        )
    if project_type is None:
        detected_type = detect_project_type(output_path.parent)
        if detected_type is None:
            raise ConfigurationError(
                "Could not automatically detect project type.",
                details="Please specify the project type with --type",
            )
        project_type = detected_type

    template = get_config_template(project_type)
    output_path.write_text(template)
    return output_path
