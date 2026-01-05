import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OpenSpecInfo:
    """Information about an OpenSpec change with open tasks."""

    name: str
    path: Path
    tasks_file: Path
    incomplete_count: int
    total_count: int


def find_open_specs(base_path: str | Path = "openspec/changes") -> list[OpenSpecInfo]:
    """
    Scans for OpenSpec changes with incomplete tasks.

    Looks for files matching: openspec/changes/*/tasks.md
    """
    base = Path(base_path)
    if not base.exists():
        return []

    specs = []
    for tasks_file in base.glob("*/tasks.md"):
        spec_path = tasks_file.parent
        spec_name = spec_path.name

        try:
            content = tasks_file.read_text()

            # Simple task pattern: - [ ] for incomplete, - [x] or - [X] for complete
            incomplete_tasks = re.findall(r"- \[ \]", content)
            complete_tasks = re.findall(r"- \[[xX]\]", content)

            incomplete_count = len(incomplete_tasks)
            total_count = incomplete_count + len(complete_tasks)

            if incomplete_count > 0:
                specs.append(
                    OpenSpecInfo(
                        name=spec_name,
                        path=spec_path,
                        tasks_file=tasks_file,
                        incomplete_count=incomplete_count,
                        total_count=total_count,
                    )
                )
        except Exception:
            # Skip invalid files or permissions issues
            continue

    # Sort by name for consistency
    return sorted(specs, key=lambda x: x.name)
