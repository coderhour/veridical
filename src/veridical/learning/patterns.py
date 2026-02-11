"""Pattern analyzer for mining work log history."""

import hashlib
import json
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path

from veridical.learning.models import (
    ErrorCategory,
    GateFailureFrequency,
    PatternReport,
    StagnationPattern,
)

logger = logging.getLogger(__name__)

# Common error category patterns
_ERROR_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "import errors",
        re.compile(r"(?:ImportError|ModuleNotFoundError|No module named)", re.IGNORECASE),
    ),
    ("type errors", re.compile(r"(?:TypeError|type error|incompatible type)", re.IGNORECASE)),
    ("syntax errors", re.compile(r"(?:SyntaxError|syntax error|unexpected token)", re.IGNORECASE)),
    ("test failures", re.compile(r"(?:FAILED|AssertionError|assert.*failed)", re.IGNORECASE)),
    ("lint errors", re.compile(r"(?:ruff|flake8|pylint|E\d{3,4}|W\d{3,4})", re.IGNORECASE)),
    ("name errors", re.compile(r"(?:NameError|undefined name|not defined)", re.IGNORECASE)),
    ("attribute errors", re.compile(r"(?:AttributeError|has no attribute)", re.IGNORECASE)),
    ("value errors", re.compile(r"(?:ValueError|invalid value|invalid literal)", re.IGNORECASE)),
    ("timeout errors", re.compile(r"(?:TimeoutError|timed out|timeout)", re.IGNORECASE)),
]


class PatternAnalyzer:
    """Analyzes work log history for recurring failure patterns."""

    def __init__(self, min_runs: int = 5) -> None:
        """Initialize the pattern analyzer.

        Args:
            min_runs: Minimum completed runs before analysis is meaningful.
        """
        self.min_runs = min_runs

    def analyze(self, worklog_dir: Path) -> PatternReport:
        """Analyze work log history for patterns.

        Args:
            worklog_dir: Path to the worklog directory containing date-based subdirectories.

        Returns:
            PatternReport with analysis results.
        """
        entries = self._load_entries(worklog_dir)

        if not entries:
            return PatternReport(
                sufficient_data=False,
                message="No work log entries found.",
                total_runs_analyzed=0,
            )

        # Group entries by run (session_id + date)
        runs = self._group_into_runs(entries)

        if len(runs) < self.min_runs:
            return PatternReport(
                sufficient_data=False,
                message=(
                    "Insufficient data for pattern analysis. "
                    f"At least {self.min_runs} completed runs are required."
                ),
                total_runs_analyzed=len(runs),
            )

        gate_frequencies = self._analyze_gate_failures(entries)
        stagnation_patterns = self._analyze_stagnation(runs)
        error_categories = self._analyze_error_categories(entries)
        avg_iterations = self._average_iterations(runs)

        return PatternReport(
            sufficient_data=True,
            total_runs_analyzed=len(runs),
            gate_failure_frequencies=gate_frequencies,
            stagnation_patterns=stagnation_patterns,
            error_categories=error_categories,
            average_iterations_per_run=avg_iterations,
        )

    def _load_entries(self, worklog_dir: Path) -> list[dict]:
        """Load all work log entries from JSONL files."""
        entries: list[dict] = []

        if not worklog_dir.exists():
            return entries

        for jsonl_file in sorted(worklog_dir.rglob("iterations.jsonl")):
            try:
                with jsonl_file.open() as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            entries.append(json.loads(line))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read {jsonl_file}: {e}")

        return entries

    def _group_into_runs(self, entries: list[dict]) -> dict[str, list[dict]]:
        """Group entries into runs by session_id."""
        runs: dict[str, list[dict]] = defaultdict(list)
        for entry in entries:
            session_id = entry.get("session_id", "unknown")
            # Use session_id + date as key to separate runs on different days
            timestamp = entry.get("timestamp", "")
            date_part = timestamp[:10] if timestamp else "unknown"
            run_key = f"{session_id}:{date_part}"
            runs[run_key].append(entry)
        return dict(runs)

    def _analyze_gate_failures(self, entries: list[dict]) -> list[GateFailureFrequency]:
        """Analyze per-gate failure frequencies from verification errors."""
        gate_failures: Counter[str] = Counter()
        gate_total: Counter[str] = Counter()
        gate_first_iter_failures: Counter[str] = Counter()
        gate_first_iter_total: Counter[str] = Counter()

        for entry in entries:
            errors = entry.get("verification_errors") or ""
            passed = entry.get("verification_passed", False)
            iteration = entry.get("iteration", 0)

            # Extract gate names from error text
            gate_names = self._extract_gate_names(errors)

            if not passed and gate_names:
                for gate in gate_names:
                    gate_failures[gate] += 1
                    gate_total[gate] += 1
                    if iteration == 1:
                        gate_first_iter_failures[gate] += 1
                        gate_first_iter_total[gate] += 1
            elif not passed and errors:
                # Generic failure without identifiable gate
                gate_failures["unknown"] += 1
                gate_total["unknown"] += 1
                if iteration == 1:
                    gate_first_iter_failures["unknown"] += 1
                    gate_first_iter_total["unknown"] += 1
            else:
                # Count total appearances for gates we've seen
                for gate in gate_total:
                    gate_total[gate] += 1
                    if iteration == 1:
                        gate_first_iter_total[gate] += 1

        frequencies = []
        for gate in gate_total:
            total = gate_total[gate]
            failures = gate_failures.get(gate, 0)
            first_total = gate_first_iter_total.get(gate, 1)
            first_failures = gate_first_iter_failures.get(gate, 0)

            frequencies.append(
                GateFailureFrequency(
                    gate_name=gate,
                    failure_count=failures,
                    total_runs=total,
                    failure_rate=round(failures / max(total, 1), 2),
                    first_iteration_failure_rate=round(first_failures / max(first_total, 1), 2),
                )
            )

        return sorted(frequencies, key=lambda f: f.failure_rate, reverse=True)

    def _extract_gate_names(self, error_text: str) -> list[str]:
        """Extract gate names from verification error text."""
        gates: list[str] = []
        # Match patterns like "Gate 'pytest' failed" or "pytest: FAILED"
        for match in re.finditer(r"(?:Gate\s+['\"](\w+)['\"]|(\w+):\s*FAILED)", error_text):
            gate = match.group(1) or match.group(2)
            if gate:
                gates.append(gate.lower())
        return gates

    def _analyze_stagnation(self, runs: dict[str, list[dict]]) -> list[StagnationPattern]:
        """Detect stagnation patterns (identical patches across iterations)."""
        # Track patch hashes across runs
        hash_to_tasks: dict[str, list[str]] = defaultdict(list)

        for _run_key, entries in runs.items():
            seen_hashes: set[str] = set()
            for entry in entries:
                patch = entry.get("patch_summary") or ""
                if patch:
                    h = hashlib.md5(patch.encode()).hexdigest()[:12]
                    if h in seen_hashes:
                        task = entry.get("task_description", "unknown")
                        hash_to_tasks[h].append(task)
                    seen_hashes.add(h)

        patterns = []
        for h, tasks in hash_to_tasks.items():
            if len(tasks) >= 2:
                patterns.append(
                    StagnationPattern(
                        diff_hash=h,
                        occurrence_count=len(tasks),
                        affected_task_descriptions=list(set(tasks)),
                    )
                )

        return sorted(patterns, key=lambda p: p.occurrence_count, reverse=True)

    def _analyze_error_categories(self, entries: list[dict]) -> list[ErrorCategory]:
        """Cluster errors into categories."""
        category_counts: Counter[str] = Counter()
        category_examples: dict[str, list[str]] = defaultdict(list)

        for entry in entries:
            errors = entry.get("verification_errors") or ""
            if not errors:
                continue

            matched = False
            for category_name, pattern in _ERROR_PATTERNS:
                if pattern.search(errors):
                    category_counts[category_name] += 1
                    if len(category_examples[category_name]) < 5:
                        # Take a short excerpt
                        excerpt = errors[:200].strip()
                        category_examples[category_name].append(excerpt)
                    matched = True

            if not matched:
                category_counts["other"] += 1
                if len(category_examples["other"]) < 5:
                    category_examples["other"].append(errors[:200].strip())

        categories = []
        for cat, count in category_counts.most_common():
            categories.append(
                ErrorCategory(
                    category=cat,
                    frequency=count,
                    example_excerpts=category_examples.get(cat, []),
                )
            )

        return categories

    def _average_iterations(self, runs: dict[str, list[dict]]) -> float:
        """Calculate average iterations per run."""
        if not runs:
            return 0.0
        total_iterations = sum(len(entries) for entries in runs.values())
        return round(total_iterations / len(runs), 1)
