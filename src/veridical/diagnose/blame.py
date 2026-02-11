import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class BlameInfo:
    author: str
    timestamp: datetime
    commit_hash: str
    line_content: str


class BlameCorrelator:
    """Identifies recent changes to code via git blame."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def get_blame(self, filename: str, line: int) -> BlameInfo | None:
        """Get git blame info for a specific line."""
        try:
            # git blame -L line,line --porcelain filename
            cmd = ["git", "blame", "-L", f"{line},{line}", "--porcelain", filename]
            result = subprocess.run(
                cmd, cwd=self.repo_path, capture_output=True, text=True, check=True
            )

            lines = result.stdout.splitlines()
            if not lines:
                return None

            # Parse porcelain output
            # First line: hash source_line result_line num_lines
            header = lines[0].split()
            if not header:
                return None
            commit_hash = header[0]

            info = {"commit_hash": commit_hash}
            for line_text in lines[1:]:
                if line_text.startswith("author "):
                    info["author"] = line_text[7:]
                elif line_text.startswith("author-time "):
                    info["timestamp"] = datetime.fromtimestamp(int(line_text[12:]))
                elif line_text.startswith("\\t"):
                    info["line_content"] = line_text[1:]
                    break

            return BlameInfo(
                author=info.get("author", "unknown"),
                timestamp=info.get("timestamp", datetime.now()),
                commit_hash=info.get("commit_hash", ""),
                line_content=info.get("line_content", ""),
            )
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError, IndexError):
            return None

    def score_recent_change(self, blame: BlameInfo) -> float:
        """Score a change based on how recent it is (higher is more likely root cause)."""
        now = datetime.now()
        delta = now - blame.timestamp

        # Simple scoring: 1.0 if within 1 hour, decaying to 0.1 after 7 days
        days = delta.total_seconds() / (24 * 3600)
        if days < 0.04:  # 1 hour
            return 1.0
        elif days < 1:
            return 0.8
        elif days < 3:
            return 0.5
        elif days < 7:
            return 0.3
        else:
            return 0.1
