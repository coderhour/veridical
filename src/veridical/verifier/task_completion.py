"""Task completion verification."""
import re
import time
from pathlib import Path

from veridical.models.result import GateResult, GateStatus

# Regex to find unchecked markdown checkboxes
INCOMPLETE_TASK_RE = re.compile(r"^\s*-\s*\[\s\]\s+(.*)$", re.MULTILINE)

# Keywords to ignore in incomplete task descriptions
IGNORED_KEYWORDS = ["manual test", "integration test"]


def verify_task_completion(gate_name: str, tasks_file_path: Path) -> GateResult:
    """Verify that all tasks in a given file are complete.

    Args:
        gate_name: The name of the quality gate.
        tasks_file_path: Path to the markdown file to check

    Returns:
        GateResult for the task completion check
    """
    start_time = time.monotonic()

    if not tasks_file_path.exists():
        return GateResult(
            name=gate_name,
            status=GateStatus.ERROR,
            error_output=f"File not found: {tasks_file_path}",
            duration_seconds=time.monotonic() - start_time,
        )

    content = tasks_file_path.read_text("utf-8")
    incomplete_tasks = INCOMPLETE_TASK_RE.findall(content)

    # Filter out ignored tasks
    actionable_incomplete = [
        task
        for task in incomplete_tasks
        if not any(keyword in task.lower() for keyword in IGNORED_KEYWORDS)
    ]

    if not actionable_incomplete:
        return GateResult(
            name=gate_name,
            status=GateStatus.PASSED,
            duration_seconds=time.monotonic() - start_time,
        )

    # Failure
    error_output = "The following tasks are not complete:\n" + "\n".join(
        f"- {task}" for task in actionable_incomplete
    )
    return GateResult(
        name=gate_name,
        status=GateStatus.FAILED,
        error_output=error_output,
        duration_seconds=time.monotonic() - start_time,
    )
