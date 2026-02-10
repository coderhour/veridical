"""Unit tests for ReportGenerator."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

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
    base_time: datetime | None = None,
    api_calls_count: int | None = None,
    estimated_tokens: int | None = None,
    vm_time_seconds: float | None = None,
) -> WorkLogEntry:
    """Helper to create a WorkLogEntry."""
    if base_time is None:
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
        api_calls_count=api_calls_count,
        estimated_tokens=estimated_tokens,
        vm_time_seconds=vm_time_seconds,
    )


def _write_jsonl(worklog_dir: Path, date: str, entries: list[WorkLogEntry]) -> None:
    """Write entries to a JSONL file under worklog_dir/date/iterations.jsonl."""
    date_dir = worklog_dir / date
    date_dir.mkdir(parents=True, exist_ok=True)
    jsonl_file = date_dir / "iterations.jsonl"
    with jsonl_file.open("w") as f:
        for entry in entries:
            f.write(entry.model_dump_json() + "\n")


class TestReportGeneratorListRuns:
    def test_list_runs_empty(self, tmp_path: Path) -> None:
        gen = ReportGenerator(tmp_path / "worklog")
        assert gen.list_runs() == []

    def test_list_runs_single_session(self, tmp_path: Path) -> None:
        worklog_dir = tmp_path / "worklog"
        entries = [
            _make_entry(1, verification_passed=False),
            _make_entry(2, verification_passed=True),
        ]
        _write_jsonl(worklog_dir, "2026-02-09", entries)

        gen = ReportGenerator(worklog_dir)
        runs = gen.list_runs()
        assert len(runs) == 1
        assert runs[0]["date"] == "2026-02-09"
        assert runs[0]["session_id"] == "sess-1"
        assert runs[0]["outcome"] == "success"
        assert runs[0]["iterations"] == "2"

    def test_list_runs_multiple_sessions(self, tmp_path: Path) -> None:
        worklog_dir = tmp_path / "worklog"
        entries = [
            _make_entry(1, session_id="sess-1", verification_passed=False),
            _make_entry(2, session_id="sess-1", verification_passed=True),
            _make_entry(1, session_id="sess-2", verification_passed=False),
        ]
        _write_jsonl(worklog_dir, "2026-02-09", entries)

        gen = ReportGenerator(worklog_dir)
        runs = gen.list_runs()
        assert len(runs) == 2


class TestReportGeneratorGenerate:
    def test_generate_no_entries(self, tmp_path: Path) -> None:
        gen = ReportGenerator(tmp_path / "worklog")
        assert gen.generate() == []

    def test_generate_latest(self, tmp_path: Path) -> None:
        worklog_dir = tmp_path / "worklog"
        entries = [
            _make_entry(
                1,
                verification_passed=False,
                verification_errors="## pytest (exit code 1)\nAssertionError",
            ),
            _make_entry(2, verification_passed=True),
        ]
        _write_jsonl(worklog_dir, "2026-02-09", entries)

        gen = ReportGenerator(worklog_dir)
        summary = gen.generate_latest()
        assert summary is not None
        assert summary.session_id == "sess-1"
        assert summary.outcome == "success"
        assert summary.total_iterations == 2
        assert summary.run_date == "2026-02-09"

    def test_generate_with_date_filter(self, tmp_path: Path) -> None:
        worklog_dir = tmp_path / "worklog"
        _write_jsonl(worklog_dir, "2026-02-09", [_make_entry(1, verification_passed=True)])
        _write_jsonl(worklog_dir, "2026-02-10", [_make_entry(1, verification_passed=False)])

        gen = ReportGenerator(worklog_dir)
        summaries = gen.generate(date="2026-02-09")
        assert len(summaries) == 1
        assert summaries[0].run_date == "2026-02-09"
        assert summaries[0].outcome == "success"

    def test_generate_with_run_id_filter(self, tmp_path: Path) -> None:
        worklog_dir = tmp_path / "worklog"
        entries = [
            _make_entry(1, session_id="sess-1", verification_passed=True),
            _make_entry(1, session_id="sess-2", verification_passed=False),
        ]
        _write_jsonl(worklog_dir, "2026-02-09", entries)

        gen = ReportGenerator(worklog_dir)
        summaries = gen.generate(run_id="sess-2")
        assert len(summaries) == 1
        assert summaries[0].session_id == "sess-2"

    def test_aggregate_metrics(self, tmp_path: Path) -> None:
        worklog_dir = tmp_path / "worklog"
        entries = [
            _make_entry(
                1,
                verification_passed=False,
                verification_errors="## pytest (exit code 1)\nfail",
                duration=15.0,
            ),
            _make_entry(
                2,
                verification_passed=False,
                verification_errors="## pytest (exit code 1)\nfail",
                duration=20.0,
            ),
            _make_entry(3, verification_passed=True, duration=10.0),
        ]
        _write_jsonl(worklog_dir, "2026-02-09", entries)

        gen = ReportGenerator(worklog_dir)
        summary = gen.generate_latest()
        assert summary is not None
        assert summary.total_iterations == 3
        assert summary.total_duration_seconds == pytest.approx(45.0)
        assert summary.most_failed_gate == "pytest"

    def test_cost_summary(self, tmp_path: Path) -> None:
        worklog_dir = tmp_path / "worklog"
        entries = [
            _make_entry(
                1,
                verification_passed=True,
                api_calls_count=5,
                estimated_tokens=1000,
                vm_time_seconds=30.0,
            ),
            _make_entry(
                2,
                verification_passed=True,
                api_calls_count=3,
                estimated_tokens=500,
                vm_time_seconds=20.0,
            ),
        ]
        _write_jsonl(worklog_dir, "2026-02-09", entries)

        gen = ReportGenerator(worklog_dir)
        summary = gen.generate_latest()
        assert summary is not None
        assert summary.cost.total_api_calls == 8
        assert summary.cost.total_estimated_tokens == 1500
        assert summary.cost.total_vm_time_seconds == pytest.approx(50.0)

    def test_malformed_jsonl_line_skipped(self, tmp_path: Path) -> None:
        worklog_dir = tmp_path / "worklog"
        date_dir = worklog_dir / "2026-02-09"
        date_dir.mkdir(parents=True)
        jsonl_file = date_dir / "iterations.jsonl"
        good_entry = _make_entry(1, verification_passed=True)
        with jsonl_file.open("w") as f:
            f.write("not valid json\n")
            f.write(good_entry.model_dump_json() + "\n")

        gen = ReportGenerator(worklog_dir)
        summary = gen.generate_latest()
        assert summary is not None
        assert summary.total_iterations == 1

    def test_per_iteration_details(self, tmp_path: Path) -> None:
        worklog_dir = tmp_path / "worklog"
        entries = [
            _make_entry(
                1,
                verification_passed=False,
                verification_errors="## ruff (exit code 1)\nE501 line too long",
                duration=5.0,
            ),
            _make_entry(2, verification_passed=True, duration=3.0),
        ]
        _write_jsonl(worklog_dir, "2026-02-09", entries)

        gen = ReportGenerator(worklog_dir)
        summary = gen.generate_latest()
        assert summary is not None
        assert len(summary.iterations) == 2
        assert summary.iterations[0].iteration == 1
        assert summary.iterations[0].gates_failed == ["ruff"]
        assert summary.iterations[0].verification_passed is False
        assert summary.iterations[0].feedback_excerpt is not None
        assert summary.iterations[1].verification_passed is True
