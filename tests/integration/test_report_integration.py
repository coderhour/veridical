"""Integration test: generate report from work log data and verify content."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from veridical.report.formatters import HtmlFormatter, JsonFormatter, TerminalFormatter
from veridical.report.generator import ReportGenerator
from veridical.worklog.models import WorkLogEntry
from veridical.worklog.writer import WorkLogWriter


class TestReportIntegration:
    """End-to-end: write work log entries → generate report → verify content."""

    def test_write_then_report_terminal(self, tmp_path: Path) -> None:
        """Write entries via WorkLogWriter, then generate a terminal report."""
        project_path = tmp_path
        writer = WorkLogWriter(project_path=project_path, log_dir="worklog")

        base_time = datetime(2026, 2, 9, 14, 0, 0)

        # Simulate 3 iterations: 2 failures then success
        entries = [
            WorkLogEntry(
                timestamp=base_time,
                iteration=1,
                session_id="integration-sess",
                task_description="Integrate feature X",
                verification_passed=False,
                verification_errors="## pytest (exit code 1)\ntest_foo failed",
                duration_seconds=12.5,
                api_calls_count=2,
                estimated_tokens=500,
            ),
            WorkLogEntry(
                timestamp=base_time + timedelta(minutes=1),
                iteration=2,
                session_id="integration-sess",
                task_description="Integrate feature X",
                verification_passed=False,
                verification_errors="## pytest (exit code 1)\ntest_foo still failing",
                duration_seconds=10.0,
                api_calls_count=2,
                estimated_tokens=400,
            ),
            WorkLogEntry(
                timestamp=base_time + timedelta(minutes=2),
                iteration=3,
                session_id="integration-sess",
                task_description="Integrate feature X",
                verification_passed=True,
                duration_seconds=8.0,
                api_calls_count=1,
                estimated_tokens=300,
            ),
        ]

        for entry in entries:
            writer.write(entry)

        # Verify the JSONL file was created
        jsonl_path = project_path / "worklog" / "2026-02-09" / "iterations.jsonl"
        assert jsonl_path.exists()

        # Generate report
        gen = ReportGenerator(project_path / "worklog")
        summary = gen.generate_latest()
        assert summary is not None
        assert summary.session_id == "integration-sess"
        assert summary.outcome == "success"
        assert summary.total_iterations == 3
        assert summary.most_failed_gate == "pytest"
        assert summary.cost.total_api_calls == 5
        assert summary.cost.total_estimated_tokens == 1200

        # Verify terminal output
        fmt = TerminalFormatter()
        output = fmt.format(summary)
        assert "integration-sess" in output
        assert "SUCCESS" in output

    def test_write_then_report_json(self, tmp_path: Path) -> None:
        """Write entries, generate JSON report, verify it parses correctly."""
        project_path = tmp_path
        writer = WorkLogWriter(project_path=project_path, log_dir="worklog")

        entry = WorkLogEntry(
            timestamp=datetime(2026, 2, 10, 9, 0, 0),
            iteration=1,
            session_id="json-sess",
            task_description="JSON test task",
            verification_passed=True,
            duration_seconds=5.0,
        )
        writer.write(entry)

        gen = ReportGenerator(project_path / "worklog")
        summary = gen.generate_latest()
        assert summary is not None

        fmt = JsonFormatter()
        result = fmt.format(summary)
        data = json.loads(result)
        assert data["session_id"] == "json-sess"
        assert data["outcome"] == "success"
        assert data["total_iterations"] == 1

    def test_write_then_report_html(self, tmp_path: Path) -> None:
        """Write entries, generate HTML report, verify structure."""
        project_path = tmp_path
        writer = WorkLogWriter(project_path=project_path, log_dir="worklog")

        entry = WorkLogEntry(
            timestamp=datetime(2026, 2, 10, 9, 0, 0),
            iteration=1,
            session_id="html-sess",
            task_description="HTML test task",
            verification_passed=False,
            verification_errors="## mypy (exit code 1)\ntype error",
            duration_seconds=7.0,
        )
        writer.write(entry)

        gen = ReportGenerator(project_path / "worklog")
        summary = gen.generate_latest()
        assert summary is not None

        fmt = HtmlFormatter()
        result = fmt.format(summary)
        assert "<!DOCTYPE html>" in result
        assert "html-sess" in result
        assert "failure" in result.lower()

    def test_list_runs_after_write(self, tmp_path: Path) -> None:
        """Write entries for multiple sessions, verify list_runs output."""
        project_path = tmp_path
        writer = WorkLogWriter(project_path=project_path, log_dir="worklog")

        base = datetime(2026, 2, 9, 10, 0, 0)
        for i, sid in enumerate(["sess-a", "sess-b"]):
            writer.write(
                WorkLogEntry(
                    timestamp=base + timedelta(hours=i),
                    iteration=1,
                    session_id=sid,
                    task_description=f"Task for {sid}",
                    verification_passed=(i == 1),
                    duration_seconds=5.0,
                )
            )

        gen = ReportGenerator(project_path / "worklog")
        runs = gen.list_runs()
        assert len(runs) == 2
        session_ids = {r["session_id"] for r in runs}
        assert session_ids == {"sess-a", "sess-b"}

    def test_report_output_to_file(self, tmp_path: Path) -> None:
        """Generate report and write to file."""
        project_path = tmp_path
        writer = WorkLogWriter(project_path=project_path, log_dir="worklog")

        writer.write(
            WorkLogEntry(
                timestamp=datetime(2026, 2, 9, 10, 0, 0),
                iteration=1,
                session_id="file-sess",
                task_description="File output test",
                verification_passed=True,
                duration_seconds=3.0,
            )
        )

        gen = ReportGenerator(project_path / "worklog")
        summary = gen.generate_latest()
        assert summary is not None

        # Write HTML to file
        fmt = HtmlFormatter()
        output_path = tmp_path / "report.html"
        output_path.write_text(fmt.format(summary))
        assert output_path.exists()
        content = output_path.read_text()
        assert "file-sess" in content
