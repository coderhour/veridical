"""Unit tests for PatternAnalyzer."""

import json
from pathlib import Path

import pytest

from veridical.learning.patterns import PatternAnalyzer


@pytest.fixture
def worklog_dir(tmp_path: Path) -> Path:
    """Create a worklog directory with sample JSONL files."""
    return tmp_path / "worklog"


def _write_entries(worklog_dir: Path, entries: list[dict], date: str = "2025-01-15") -> None:
    """Helper to write entries to a JSONL file."""
    date_dir = worklog_dir / date
    date_dir.mkdir(parents=True, exist_ok=True)
    with (date_dir / "iterations.jsonl").open("a") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def _make_entry(
    iteration: int = 1,
    session_id: str = "sess-1",
    task: str = "Fix the bug",
    passed: bool = False,
    errors: str | None = None,
    patch_summary: str | None = None,
    date: str = "2025-01-15",
) -> dict:
    return {
        "timestamp": f"{date}T10:00:00",
        "iteration": iteration,
        "session_id": session_id,
        "task_description": task,
        "verification_passed": passed,
        "verification_errors": errors,
        "patch_summary": patch_summary,
    }


class TestPatternAnalyzer:
    def test_analyze_empty_dir(self, worklog_dir: Path) -> None:
        analyzer = PatternAnalyzer(min_runs=5)
        report = analyzer.analyze(worklog_dir)
        assert not report.sufficient_data
        assert report.total_runs_analyzed == 0

    def test_analyze_nonexistent_dir(self, tmp_path: Path) -> None:
        analyzer = PatternAnalyzer(min_runs=5)
        report = analyzer.analyze(tmp_path / "nonexistent")
        assert not report.sufficient_data

    def test_analyze_insufficient_data(self, worklog_dir: Path) -> None:
        # Only 3 runs, need 5
        for i in range(3):
            _write_entries(
                worklog_dir, [_make_entry(session_id=f"sess-{i}")], date=f"2025-01-{15 + i:02d}"
            )

        analyzer = PatternAnalyzer(min_runs=5)
        report = analyzer.analyze(worklog_dir)
        assert not report.sufficient_data
        assert "At least 5 completed runs" in (report.message or "")

    def test_analyze_sufficient_data(self, worklog_dir: Path) -> None:
        for i in range(6):
            _write_entries(
                worklog_dir,
                [_make_entry(session_id=f"sess-{i}", errors="Gate 'pytest' FAILED")],
                date=f"2025-01-{15 + i:02d}",
            )

        analyzer = PatternAnalyzer(min_runs=5)
        report = analyzer.analyze(worklog_dir)
        assert report.sufficient_data
        assert report.total_runs_analyzed == 6

    def test_gate_failure_frequencies(self, worklog_dir: Path) -> None:
        entries = []
        for i in range(6):
            entries.append(
                _make_entry(
                    session_id=f"sess-{i}",
                    errors="Gate 'pytest' FAILED" if i < 4 else None,
                    passed=i >= 4,
                )
            )
            _write_entries(worklog_dir, [entries[-1]], date=f"2025-01-{15 + i:02d}")

        analyzer = PatternAnalyzer(min_runs=5)
        report = analyzer.analyze(worklog_dir)
        assert report.sufficient_data
        assert len(report.gate_failure_frequencies) > 0

        pytest_gate = next(
            (f for f in report.gate_failure_frequencies if f.gate_name == "pytest"), None
        )
        assert pytest_gate is not None
        assert pytest_gate.failure_count >= 4

    def test_error_category_clustering(self, worklog_dir: Path) -> None:
        for i in range(6):
            error = (
                "ImportError: No module named 'foo'" if i < 3 else "TypeError: incompatible type"
            )
            _write_entries(
                worklog_dir,
                [_make_entry(session_id=f"sess-{i}", errors=error)],
                date=f"2025-01-{15 + i:02d}",
            )

        analyzer = PatternAnalyzer(min_runs=5)
        report = analyzer.analyze(worklog_dir)
        assert report.sufficient_data
        assert len(report.error_categories) >= 2

        categories = {c.category for c in report.error_categories}
        assert "import errors" in categories
        assert "type errors" in categories

    def test_stagnation_detection(self, worklog_dir: Path) -> None:
        for i in range(6):
            entries = [
                _make_entry(
                    iteration=1, session_id=f"sess-{i}", patch_summary="same patch content"
                ),
                _make_entry(
                    iteration=2, session_id=f"sess-{i}", patch_summary="same patch content"
                ),
            ]
            _write_entries(worklog_dir, entries, date=f"2025-01-{15 + i:02d}")

        analyzer = PatternAnalyzer(min_runs=5)
        report = analyzer.analyze(worklog_dir)
        assert report.sufficient_data
        assert len(report.stagnation_patterns) > 0

    def test_average_iterations(self, worklog_dir: Path) -> None:
        for i in range(6):
            iters = 3 if i < 3 else 1
            entries = [_make_entry(iteration=j + 1, session_id=f"sess-{i}") for j in range(iters)]
            _write_entries(worklog_dir, entries, date=f"2025-01-{15 + i:02d}")

        analyzer = PatternAnalyzer(min_runs=5)
        report = analyzer.analyze(worklog_dir)
        assert report.sufficient_data
        assert report.average_iterations_per_run == 2.0

    def test_custom_min_runs(self, worklog_dir: Path) -> None:
        for i in range(3):
            _write_entries(
                worklog_dir, [_make_entry(session_id=f"sess-{i}")], date=f"2025-01-{15 + i:02d}"
            )

        analyzer = PatternAnalyzer(min_runs=2)
        report = analyzer.analyze(worklog_dir)
        assert report.sufficient_data
