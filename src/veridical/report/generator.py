"""Report generator that parses work log JSONL files into structured summaries."""

import json
import logging
from collections import Counter
from pathlib import Path

from veridical.report.models import (
    CostSummary,
    IterationDetail,
    PatternInsight,
    RunSummary,
)
from veridical.worklog.models import WorkLogEntry

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Parses work log JSONL files and produces structured run summaries."""

    def __init__(self, worklog_dir: Path) -> None:
        """Initialize the report generator.

        Args:
            worklog_dir: Path to the worklog directory (e.g. <project>/worklog)
        """
        self.worklog_dir = worklog_dir

    def list_runs(self) -> list[dict[str, str]]:
        """List all available runs from the worklog directory.

        Returns:
            List of dicts with keys: date, session_id, task_description, outcome, iterations
        """
        runs: list[dict[str, str]] = []
        if not self.worklog_dir.exists():
            return runs

        for date_dir in sorted(self.worklog_dir.iterdir()):
            if not date_dir.is_dir():
                continue
            jsonl_file = date_dir / "iterations.jsonl"
            if not jsonl_file.exists():
                continue

            entries = self._parse_jsonl(jsonl_file)
            if not entries:
                continue

            # Group by session_id
            sessions: dict[str, list[WorkLogEntry]] = {}
            for entry in entries:
                sessions.setdefault(entry.session_id, []).append(entry)

            for session_id, session_entries in sessions.items():
                last = session_entries[-1]
                outcome = "success" if last.verification_passed else "failure"
                runs.append(
                    {
                        "date": date_dir.name,
                        "session_id": session_id,
                        "task_description": session_entries[0].task_description,
                        "outcome": outcome,
                        "iterations": str(len(session_entries)),
                    }
                )

        return runs

    def generate(
        self,
        *,
        date: str | None = None,
        run_id: str | None = None,
    ) -> list[RunSummary]:
        """Generate run summaries from work log data.

        Args:
            date: Optional date filter (YYYY-MM-DD)
            run_id: Optional session ID filter

        Returns:
            List of RunSummary objects
        """
        entries = self._load_entries(date=date)
        if not entries:
            return []

        # Group by session_id
        sessions: dict[str, list[WorkLogEntry]] = {}
        for entry in entries:
            sessions.setdefault(entry.session_id, []).append(entry)

        # Filter by run_id if specified
        if run_id:
            sessions = {k: v for k, v in sessions.items() if k == run_id}

        summaries: list[RunSummary] = []
        for session_id, session_entries in sessions.items():
            summary = self._build_summary(session_id, session_entries)
            summaries.append(summary)

        return summaries

    def generate_latest(self) -> RunSummary | None:
        """Generate a summary for the most recent run.

        Returns:
            RunSummary for the latest run, or None if no runs exist
        """
        entries = self._load_entries()
        if not entries:
            return None

        # Group by session_id and pick the one with the latest timestamp
        sessions: dict[str, list[WorkLogEntry]] = {}
        for entry in entries:
            sessions.setdefault(entry.session_id, []).append(entry)

        if not sessions:
            return None

        # Find session with latest last entry
        latest_session_id = max(
            sessions,
            key=lambda sid: sessions[sid][-1].timestamp,
        )
        return self._build_summary(latest_session_id, sessions[latest_session_id])

    def _load_entries(self, *, date: str | None = None) -> list[WorkLogEntry]:
        """Load work log entries, optionally filtered by date."""
        if not self.worklog_dir.exists():
            return []

        entries: list[WorkLogEntry] = []
        for date_dir in sorted(self.worklog_dir.iterdir()):
            if not date_dir.is_dir():
                continue
            if date and date_dir.name != date:
                continue
            jsonl_file = date_dir / "iterations.jsonl"
            if jsonl_file.exists():
                entries.extend(self._parse_jsonl(jsonl_file))

        return entries

    def _parse_jsonl(self, path: Path) -> list[WorkLogEntry]:
        """Parse a JSONL file into WorkLogEntry objects."""
        entries: list[WorkLogEntry] = []
        for line_num, line in enumerate(path.read_text().splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entries.append(WorkLogEntry(**data))
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Skipping malformed line {line_num} in {path}: {e}")
        return entries

    def _build_summary(self, session_id: str, entries: list[WorkLogEntry]) -> RunSummary:
        """Build a RunSummary from a list of entries for a single session."""
        entries.sort(key=lambda e: e.timestamp)

        first = entries[0]
        last = entries[-1]
        outcome = "success" if last.verification_passed else "failure"

        # Build iteration details
        iterations: list[IterationDetail] = []
        gate_failure_counter: Counter[str] = Counter()

        for entry in entries:
            # Parse gate info from verification_errors
            gates_failed = self._extract_failed_gates(entry.verification_errors)
            for g in gates_failed:
                gate_failure_counter[g] += 1

            feedback_excerpt = None
            if entry.verification_errors:
                feedback_excerpt = entry.verification_errors[:200]

            detail = IterationDetail(
                iteration=entry.iteration,
                timestamp=entry.timestamp,
                duration_seconds=entry.duration_seconds,
                gates_failed=gates_failed,
                verification_passed=entry.verification_passed,
                feedback_excerpt=feedback_excerpt,
                api_calls_count=entry.api_calls_count,
                estimated_tokens=entry.estimated_tokens,
                vm_time_seconds=entry.vm_time_seconds,
            )
            iterations.append(detail)

        # Aggregate metrics
        total_duration = sum(e.duration_seconds for e in entries if e.duration_seconds is not None)
        most_failed = gate_failure_counter.most_common(1)
        most_failed_gate = most_failed[0][0] if most_failed else None

        # Cost summary
        cost = CostSummary(
            total_api_calls=sum(
                e.api_calls_count for e in entries if e.api_calls_count is not None
            ),
            total_estimated_tokens=sum(
                e.estimated_tokens for e in entries if e.estimated_tokens is not None
            ),
            total_vm_time_seconds=sum(
                e.vm_time_seconds for e in entries if e.vm_time_seconds is not None
            ),
        )

        # Pattern detection
        patterns = self._detect_patterns(entries, gate_failure_counter)

        return RunSummary(
            run_date=first.timestamp.strftime("%Y-%m-%d"),
            session_id=session_id,
            task_description=first.task_description,
            outcome=outcome,
            total_iterations=len(entries),
            total_duration_seconds=total_duration if total_duration > 0 else None,
            started_at=first.timestamp,
            completed_at=last.timestamp,
            most_failed_gate=most_failed_gate,
            cost=cost,
            iterations=iterations,
            patterns=patterns,
        )

    def _extract_failed_gates(self, verification_errors: str | None) -> list[str]:
        """Extract gate names from verification error text.

        The feedback format is typically:
            ## gate_name (exit code N)
            <error details>
        """
        if not verification_errors:
            return []

        gates: list[str] = []
        for line in verification_errors.splitlines():
            line = line.strip()
            if line.startswith("## ") and "(" in line:
                gate_name = line[3:].split("(")[0].strip()
                if gate_name:
                    gates.append(gate_name)
        return gates

    def _detect_patterns(
        self,
        entries: list[WorkLogEntry],
        gate_failure_counter: Counter[str],
    ) -> list[PatternInsight]:
        """Detect patterns in run data."""
        patterns: list[PatternInsight] = []

        # 4.1: Gate failure frequency analysis
        for gate_name, count in gate_failure_counter.most_common():
            if count >= 2:
                failed_iters = [
                    e.iteration
                    for e in entries
                    if gate_name in self._extract_failed_gates(e.verification_errors)
                ]
                patterns.append(
                    PatternInsight(
                        category="frequent_failure",
                        description=(
                            f"Gate '{gate_name}' failed on {count}/{len(entries)} iterations"
                        ),
                        gate_name=gate_name,
                        iterations_affected=failed_iters,
                    )
                )

        # 4.2: Gates that fail on first iteration but pass on retry
        if len(entries) >= 2:
            first_entry = entries[0]
            last_entry = entries[-1]
            first_failed = set(self._extract_failed_gates(first_entry.verification_errors))
            last_failed = set(self._extract_failed_gates(last_entry.verification_errors))
            # Gates that failed first but eventually passed
            recovered = first_failed - last_failed
            if last_entry.verification_passed:
                recovered = first_failed  # All gates eventually passed
            for gate_name in recovered:
                patterns.append(
                    PatternInsight(
                        category="first_iter_failure",
                        description=(
                            f"Gate '{gate_name}' failed on first iteration "
                            f"but passed on retry (prompt improvement candidate)"
                        ),
                        gate_name=gate_name,
                        iterations_affected=[1],
                    )
                )

        # 4.3: Stagnation detection - same gate failing repeatedly with same error
        if len(entries) >= 3:
            for i in range(len(entries) - 2):
                window = entries[i : i + 3]
                errors = [e.verification_errors for e in window]
                if all(errors) and len(set(errors)) == 1:
                    iters = [e.iteration for e in window]
                    patterns.append(
                        PatternInsight(
                            category="stagnation",
                            description=(
                                f"Stagnation detected: same error on "
                                f"iterations {iters[0]}-{iters[-1]}"
                            ),
                            iterations_affected=iters,
                        )
                    )
                    break  # Report only the first stagnation window

        return patterns
