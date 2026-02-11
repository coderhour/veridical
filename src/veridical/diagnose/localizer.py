import logging
from dataclasses import dataclass, field
from pathlib import Path

from veridical.diagnose.blame import BlameCorrelator
from veridical.diagnose.call_graph import CallGraphAnalyzer
from veridical.diagnose.stack_trace import StackTraceParser

logger = logging.getLogger(__name__)


@dataclass
class LocalizationEntry:
    file: str
    line: int
    function: str
    confidence: float
    reason: str


@dataclass
class LocalizationReport:
    entries: list[LocalizationEntry] = field(default_factory=list)

    def to_feedback_string(self) -> str:
        if not self.entries:
            return ""

        # Take the top candidate
        top = sorted(self.entries, key=lambda x: x.confidence, reverse=True)[0]
        return f"Root cause likely in {top.file}:{top.line} ({top.reason})"


class Localizer:
    """Orchestrates all signals into a ranked LocalizationReport."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.stack_parser = StackTraceParser(repo_path)
        self.blame_correlator = BlameCorrelator(repo_path)
        self.call_analyzer = CallGraphAnalyzer(repo_path)

    def localize(self, error_text: str) -> LocalizationReport:
        """Analyze error text and return ranked candidates."""
        frames = self.stack_parser.parse(error_text)
        if not frames:
            return LocalizationReport()

        candidates = []

        # 1. Analyze the stack trace frames
        # Usually the deepest frame in the app code is the most likely crash site
        app_frames = [f for f in frames if not self._is_library_code(f.filename)]

        if not app_frames:
            # If all frames are library code, take the first one (most recent call)
            app_frames = frames[:1]

        for i, frame in enumerate(app_frames):
            # Base confidence: 0.8 for most recent app frame, decreasing
            base_confidence = 0.8 * (0.8**i)
            reason = "Crash site in stack trace"

            # Enrich with blame info
            blame = self.blame_correlator.get_blame(frame.filename, frame.line)
            if blame:
                recency_score = self.blame_correlator.score_recent_change(blame)
                if recency_score > 0.5:
                    base_confidence += 0.2
                    reason += " (recently modified)"

            candidates.append(
                LocalizationEntry(
                    file=frame.filename,
                    line=frame.line,
                    function=frame.function,
                    confidence=min(0.95, base_confidence),
                    reason=reason,
                )
            )

            # 2. Use call graph to find callers (potential root causes)
            if frame.function and frame.function != "unknown":
                callers = self.call_analyzer.find_callers(frame.function)
                for caller in callers[:3]:  # Limit to top 3 callers to avoid noise
                    candidates.append(
                        LocalizationEntry(
                            file=caller["file"],
                            line=caller["line"],
                            function=caller["function"],
                            confidence=base_confidence * 0.4,
                            reason=f"Calls into suspected crash site {frame.function}",
                        )
                    )

        return LocalizationReport(entries=candidates)

    def _is_library_code(self, filename: str) -> bool:
        """Simple check if file is in site-packages or standard lib."""
        lib_markers = ["site-packages", "/usr/lib", "lib/python", "node_modules"]
        return any(marker in filename for marker in lib_markers)
