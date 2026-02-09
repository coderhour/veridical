"""Work log writer for persisting entries to disk."""

import logging
from pathlib import Path

from veridical.worklog.models import WorkLogEntry

logger = logging.getLogger(__name__)


class WorkLogWriter:
    """Writes work log entries to date-organized JSONL files.

    Entries are written to `{log_dir}/YYYY-MM-DD/iterations.jsonl` where
    the date is determined by the entry's timestamp.
    """

    def __init__(self, project_path: Path, log_dir: str = "worklog") -> None:
        """Initialize the work log writer.

        Args:
            project_path: Path to the project root (where .veridical.yaml exists)
            log_dir: Directory name for logs relative to project_path (default: "worklog")
        """
        self.project_path = project_path
        self.log_dir = project_path / log_dir

    def write(self, entry: WorkLogEntry) -> None:
        """Write an entry to the work log.

        Creates the date-based directory structure if it doesn't exist and
        appends the entry as a JSON line to the appropriate file.

        Args:
            entry: The work log entry to write
        """
        # Determine the date-based subdirectory
        date_str = entry.timestamp.strftime("%Y-%m-%d")
        date_dir = self.log_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)

        # Append to the JSONL file
        log_file = date_dir / "iterations.jsonl"
        with log_file.open("a") as f:
            f.write(entry.model_dump_json() + "\n")

        logger.debug(f"Wrote work log entry to {log_file}")
