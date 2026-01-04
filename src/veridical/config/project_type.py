"""Project type detection."""

from pathlib import Path

from .defaults import ProjectType


def detect_project_type(path: Path | None = None) -> ProjectType | None:
    """Detect the project type based on characteristic files."""
    search_path = path or Path.cwd()

    # JavaScript check
    if (search_path / "package.json").exists():
        return "javascript"

    # Python check
    if (
        (search_path / "pyproject.toml").exists()
        or (search_path / "setup.py").exists()
        or (search_path / "requirements.txt").exists()
    ):
        return "python"

    return None
