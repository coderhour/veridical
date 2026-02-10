"""Unit tests for pattern detection logic in ReportGenerator."""

from datetime import datetime, timedelta
from pathlib import Path

from veridical.report.generator import ReportGenerator
from veridical.worklog.models import WorkLogEntry


def _make_entry(
    iteration: int,
    *,
    session_id: str = "sess-1",
    task: str = "Fix the bug",
    verification_passed: bool = False,
    verification_errors: str | None = None,
    duration: float = 10.0,
) -> WorkLogEntry:
    base_time = datetime(2026, 2, 9, 10, 0, 0)
    ts = base_time + timedelta(seconds=iteration * 60)
    return WorkLogEntry(
        timestamp=ts,
        iteration=iteration,
        session_id=session_id,
        task_description=task,
        verification_passed=verification_passed,
        verification_errors=verification_errors,
        duration_seconds=duration,
    )


def _write_jsonl(worklog_dir: Path, date: str, entries: list[WorkLogEntry]) -> None:
    date_dir = worklog_dir / date
    date_dir.mkdir(parents=True, exist_ok=True)
    jsonl_file = date_dir / "iterations.jsonl"
    with jsonl_file.open("w") as f:
        for entry in entries:
            f.write(entry.model_dump_json() + "\n")


class TestFrequentFailurePattern:
    def test_detects_frequent_gate_failure(self, tmp_path: Path) -> None:
        worklog_dir = tmp_path / "worklog"
        entries = [
            _make_entry(1, verification_errors="## pytest (exit code 1)\nfail1"),
            _make_entry(2, verification_errors="## pytest (exit code 1)\nfail2"),
            _make_entry(3, verification_passed=True),
        ]
        _write_jsonl(worklog_dir, "2026-02-09", entries)

        gen = ReportGenerator(worklog_dir)
        summary = gen.generate_latest()
        assert summary is not None

        freq_patterns = [p for p in summary.patterns if p.category == "frequent_failure"]
        assert len(freq_patterns) >= 1
        assert freq_patterns[0].gate_name == "pytest"
        assert "2/" in freq_patterns[0].description

    def test_no_pattern_for_single_failure(self, tmp_path: Path) -> None:
        worklog_dir = tmp_path / "worklog"
        entries = [
            _make_entry(1, verification_errors="## pytest (exit code 1)\nfail"),
            _make_entry(2, verification_passed=True),
        ]
        _write_jsonl(worklog_dir, "2026-02-09", entries)

        gen = ReportGenerator(worklog_dir)
        summary = gen.generate_latest()
        assert summary is not None

        freq_patterns = [p for p in summary.patterns if p.category == "frequent_failure"]
        assert len(freq_patterns) == 0


class TestFirstIterFailurePattern:
    def test_detects_first_iter_failure_then_pass(self, tmp_path: Path) -> None:
        worklog_dir = tmp_path / "worklog"
        entries = [
            _make_entry(1, verification_errors="## ruff (exit code 1)\nE501"),
            _make_entry(2, verification_passed=True),
        ]
        _write_jsonl(worklog_dir, "2026-02-09", entries)

        gen = ReportGenerator(worklog_dir)
        summary = gen.generate_latest()
        assert summary is not None

        first_iter_patterns = [p for p in summary.patterns if p.category == "first_iter_failure"]
        assert len(first_iter_patterns) >= 1
        assert first_iter_patterns[0].gate_name == "ruff"
        assert "prompt improvement" in first_iter_patterns[0].description

    def test_no_pattern_when_single_iteration(self, tmp_path: Path) -> None:
        worklog_dir = tmp_path / "worklog"
        entries = [
            _make_entry(1, verification_passed=True),
        ]
        _write_jsonl(worklog_dir, "2026-02-09", entries)

        gen = ReportGenerator(worklog_dir)
        summary = gen.generate_latest()
        assert summary is not None

        first_iter_patterns = [p for p in summary.patterns if p.category == "first_iter_failure"]
        assert len(first_iter_patterns) == 0


class TestStagnationPattern:
    def test_detects_stagnation(self, tmp_path: Path) -> None:
        same_error = "## pytest (exit code 1)\nAssertionError: x != y"
        worklog_dir = tmp_path / "worklog"
        entries = [
            _make_entry(1, verification_errors=same_error),
            _make_entry(2, verification_errors=same_error),
            _make_entry(3, verification_errors=same_error),
        ]
        _write_jsonl(worklog_dir, "2026-02-09", entries)

        gen = ReportGenerator(worklog_dir)
        summary = gen.generate_latest()
        assert summary is not None

        stag_patterns = [p for p in summary.patterns if p.category == "stagnation"]
        assert len(stag_patterns) >= 1
        assert "iterations 1-3" in stag_patterns[0].description

    def test_no_stagnation_with_different_errors(self, tmp_path: Path) -> None:
        worklog_dir = tmp_path / "worklog"
        entries = [
            _make_entry(1, verification_errors="## pytest (exit code 1)\nerror A"),
            _make_entry(2, verification_errors="## pytest (exit code 1)\nerror B"),
            _make_entry(3, verification_errors="## pytest (exit code 1)\nerror C"),
        ]
        _write_jsonl(worklog_dir, "2026-02-09", entries)

        gen = ReportGenerator(worklog_dir)
        summary = gen.generate_latest()
        assert summary is not None

        stag_patterns = [p for p in summary.patterns if p.category == "stagnation"]
        assert len(stag_patterns) == 0

    def test_no_stagnation_with_fewer_than_3_iterations(self, tmp_path: Path) -> None:
        same_error = "## pytest (exit code 1)\nsame"
        worklog_dir = tmp_path / "worklog"
        entries = [
            _make_entry(1, verification_errors=same_error),
            _make_entry(2, verification_errors=same_error),
        ]
        _write_jsonl(worklog_dir, "2026-02-09", entries)

        gen = ReportGenerator(worklog_dir)
        summary = gen.generate_latest()
        assert summary is not None

        stag_patterns = [p for p in summary.patterns if p.category == "stagnation"]
        assert len(stag_patterns) == 0


class TestPatternInsightsInReport:
    def test_patterns_included_for_3plus_iterations(self, tmp_path: Path) -> None:
        """Spec: pattern insights shown for runs with 3+ iterations."""
        worklog_dir = tmp_path / "worklog"
        entries = [
            _make_entry(1, verification_errors="## pytest (exit code 1)\nfail"),
            _make_entry(2, verification_errors="## pytest (exit code 1)\nfail"),
            _make_entry(3, verification_passed=True),
        ]
        _write_jsonl(worklog_dir, "2026-02-09", entries)

        gen = ReportGenerator(worklog_dir)
        summary = gen.generate_latest()
        assert summary is not None
        assert len(summary.patterns) > 0
