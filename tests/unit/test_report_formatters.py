"""Unit tests for report output formatters."""

import json
from datetime import datetime

import pytest

from veridical.report.formatters import (
    HtmlFormatter,
    JsonFormatter,
    TerminalFormatter,
    get_formatter,
)
from veridical.report.models import (
    CostSummary,
    IterationDetail,
    PatternInsight,
    RunSummary,
)


@pytest.fixture
def sample_summary() -> RunSummary:
    """Create a sample RunSummary for testing."""
    return RunSummary(
        run_date="2026-02-09",
        session_id="sess-abc",
        task_description="Fix the flaky test",
        outcome="success",
        total_iterations=3,
        total_duration_seconds=45.0,
        started_at=datetime(2026, 2, 9, 10, 0, 0),
        completed_at=datetime(2026, 2, 9, 10, 0, 45),
        most_failed_gate="pytest",
        cost=CostSummary(
            total_api_calls=8,
            total_estimated_tokens=1500,
            total_vm_time_seconds=30.0,
        ),
        iterations=[
            IterationDetail(
                iteration=1,
                timestamp=datetime(2026, 2, 9, 10, 0, 0),
                duration_seconds=15.0,
                gates_failed=["pytest"],
                verification_passed=False,
                feedback_excerpt="AssertionError: expected True",
            ),
            IterationDetail(
                iteration=2,
                timestamp=datetime(2026, 2, 9, 10, 0, 15),
                duration_seconds=20.0,
                gates_failed=["pytest"],
                verification_passed=False,
                feedback_excerpt="AssertionError: still failing",
            ),
            IterationDetail(
                iteration=3,
                timestamp=datetime(2026, 2, 9, 10, 0, 35),
                duration_seconds=10.0,
                gates_failed=[],
                verification_passed=True,
            ),
        ],
        patterns=[
            PatternInsight(
                category="frequent_failure",
                description="Gate 'pytest' failed on 2/3 iterations",
                gate_name="pytest",
                iterations_affected=[1, 2],
            ),
        ],
    )


class TestTerminalFormatter:
    def test_renders_string(self, sample_summary: RunSummary) -> None:
        fmt = TerminalFormatter()
        result = fmt.format(sample_summary)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_session_id(self, sample_summary: RunSummary) -> None:
        fmt = TerminalFormatter()
        result = fmt.format(sample_summary)
        assert "sess-abc" in result

    def test_contains_outcome(self, sample_summary: RunSummary) -> None:
        fmt = TerminalFormatter()
        result = fmt.format(sample_summary)
        assert "SUCCESS" in result

    def test_contains_iteration_count(self, sample_summary: RunSummary) -> None:
        fmt = TerminalFormatter()
        result = fmt.format(sample_summary)
        assert "3" in result

    def test_contains_pattern_insight(self, sample_summary: RunSummary) -> None:
        fmt = TerminalFormatter()
        result = fmt.format(sample_summary)
        assert "pytest" in result
        assert "failed on" in result


class TestJsonFormatter:
    def test_valid_json(self, sample_summary: RunSummary) -> None:
        fmt = JsonFormatter()
        result = fmt.format(sample_summary)
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_contains_fields(self, sample_summary: RunSummary) -> None:
        fmt = JsonFormatter()
        result = fmt.format(sample_summary)
        data = json.loads(result)
        assert data["session_id"] == "sess-abc"
        assert data["outcome"] == "success"
        assert data["total_iterations"] == 3
        assert len(data["iterations"]) == 3
        assert len(data["patterns"]) == 1

    def test_cost_in_json(self, sample_summary: RunSummary) -> None:
        fmt = JsonFormatter()
        result = fmt.format(sample_summary)
        data = json.loads(result)
        assert data["cost"]["total_api_calls"] == 8
        assert data["cost"]["total_estimated_tokens"] == 1500


class TestHtmlFormatter:
    def test_valid_html(self, sample_summary: RunSummary) -> None:
        fmt = HtmlFormatter()
        result = fmt.format(sample_summary)
        assert result.startswith("<!DOCTYPE html>")
        assert "</html>" in result

    def test_contains_session_id(self, sample_summary: RunSummary) -> None:
        fmt = HtmlFormatter()
        result = fmt.format(sample_summary)
        assert "sess-abc" in result

    def test_contains_outcome_class(self, sample_summary: RunSummary) -> None:
        fmt = HtmlFormatter()
        result = fmt.format(sample_summary)
        assert 'class="outcome success"' in result

    def test_failure_outcome_class(self, sample_summary: RunSummary) -> None:
        summary = sample_summary.model_copy(update={"outcome": "failure"})
        fmt = HtmlFormatter()
        result = fmt.format(summary)
        assert 'class="outcome failure"' in result

    def test_contains_iteration_rows(self, sample_summary: RunSummary) -> None:
        fmt = HtmlFormatter()
        result = fmt.format(sample_summary)
        # Each iteration row starts with <tr><td>N</td> where N is the iteration number
        for i in range(1, 4):
            assert f"<tr><td>{i}</td>" in result

    def test_html_escaping(self) -> None:
        summary = RunSummary(
            run_date="2026-02-09",
            session_id="<script>alert('xss')</script>",
            task_description="Fix <b>bold</b> issue",
            outcome="success",
            total_iterations=1,
            started_at=datetime(2026, 2, 9, 10, 0, 0),
            completed_at=datetime(2026, 2, 9, 10, 0, 10),
            iterations=[
                IterationDetail(
                    iteration=1,
                    timestamp=datetime(2026, 2, 9, 10, 0, 0),
                    verification_passed=True,
                ),
            ],
        )
        fmt = HtmlFormatter()
        result = fmt.format(summary)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_cost_section_shown_when_present(self, sample_summary: RunSummary) -> None:
        fmt = HtmlFormatter()
        result = fmt.format(sample_summary)
        assert "Cost Summary" in result

    def test_cost_section_hidden_when_zero(self) -> None:
        summary = RunSummary(
            run_date="2026-02-09",
            session_id="sess-1",
            task_description="task",
            outcome="success",
            total_iterations=1,
            started_at=datetime(2026, 2, 9, 10, 0, 0),
            completed_at=datetime(2026, 2, 9, 10, 0, 10),
            iterations=[
                IterationDetail(
                    iteration=1,
                    timestamp=datetime(2026, 2, 9, 10, 0, 0),
                    verification_passed=True,
                ),
            ],
        )
        fmt = HtmlFormatter()
        result = fmt.format(summary)
        assert "Cost Summary" not in result


class TestGetFormatter:
    def test_terminal(self) -> None:
        assert isinstance(get_formatter("terminal"), TerminalFormatter)

    def test_json(self) -> None:
        assert isinstance(get_formatter("json"), JsonFormatter)

    def test_html(self) -> None:
        assert isinstance(get_formatter("html"), HtmlFormatter)

    def test_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown format"):
            get_formatter("pdf")
