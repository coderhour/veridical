import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


@dataclass(frozen=True)
class StackFrame:
    filename: str
    line: int
    function: str
    context: str | None = None


class StackTraceParser:
    """Parses stack traces to extract file and line information."""

    # Pattern for Python tracebacks: File "path/to/file.py", line 123, in function_name
    PYTHON_PATTERN = re.compile(r'File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<func>\w+)')

    # Generic patterns: path/to/file.py:123, path/to/file.py(123), etc.
    GENERIC_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"(?P<file>[\w\./-]+):(?P<line>\d+)"),
        re.compile(r"(?P<file>[\w\./-]+)\((?P<line>\d+)\)"),
        re.compile(r"at (?P<file>[\w\./-]+):(?P<line>\d+)"),
    ]

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def parse(self, text: str) -> list[StackFrame]:
        """Extract stack frames from text."""
        frames = []

        # Try Python traceback pattern first
        for match in self.PYTHON_PATTERN.finditer(text):
            frames.append(
                StackFrame(
                    filename=match.group("file"),
                    line=int(match.group("line")),
                    function=match.group("func"),
                )
            )

        if frames:
            # We want most recent call first for localization
            return list(reversed(frames))

        # Fallback to generic patterns
        for pattern in self.GENERIC_PATTERNS:
            for match in pattern.finditer(text):
                file_path = match.group("file")
                # Avoid duplicates if multiple patterns match same thing
                if not any(
                    f.filename == file_path and f.line == int(match.group("line")) for f in frames
                ):
                    frames.append(
                        StackFrame(
                            filename=file_path, line=int(match.group("line")), function="unknown"
                        )
                    )

        return frames
