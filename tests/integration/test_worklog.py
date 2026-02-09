"""Integration tests for work log functionality."""

import json
from datetime import datetime
from pathlib import Path

from veridical.worklog import WorkLogEntry, WorkLogWriter


def test_worklog_integration_full_workflow(tmp_path: Path):
    """Test complete work log workflow with realistic data."""
    writer = WorkLogWriter(project_path=tmp_path, log_dir="worklog")

    # Simulate iteration 1: success
    entry1 = WorkLogEntry(
        timestamp=datetime(2026, 2, 6, 15, 0, 0),
        iteration=1,
        session_id="session-abc-123",
        task_description="Implement user authentication",
        error_context=None,
        prompt_sent="Implement JWT-based authentication",
        session_status="completed",
        verification_passed=True,
        verification_errors=None,
        duration_seconds=180.5,
    )
    writer.write(entry1)

    # Simulate iteration 2: failure
    entry2 = WorkLogEntry(
        timestamp=datetime(2026, 2, 6, 15, 10, 0),
        iteration=2,
        session_id="session-abc-124",
        task_description="Add password reset feature",
        error_context="Tests failed in previous iteration",
        prompt_sent="Fix the failing authentication tests",
        session_status="completed",
        verification_passed=False,
        verification_errors="AssertionError: Expected 200, got 401",
        duration_seconds=95.2,
    )
    writer.write(entry2)

    # Simulate iteration 3: interrupted
    entry3 = WorkLogEntry(
        timestamp=datetime(2026, 2, 6, 15, 20, 0),
        iteration=3,
        session_id="session-abc-125",
        task_description="Add password reset feature",
        error_context="AssertionError: Expected 200, got 401",
        prompt_sent="Fix authentication status code",
        session_status="interrupted",
        verification_passed=None,
        verification_errors=None,
        duration_seconds=45.0,
    )
    writer.write(entry3)

    # Verify the log file
    log_file = tmp_path / "worklog" / "2026-02-06" / "iterations.jsonl"
    assert log_file.exists()

    # Read and parse all entries
    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 3

    # Verify entry 1
    data1 = json.loads(lines[0])
    assert data1["iteration"] == 1
    assert data1["session_id"] == "session-abc-123"
    assert data1["verification_passed"] is True
    assert data1["duration_seconds"] == 180.5

    # Verify entry 2
    data2 = json.loads(lines[1])
    assert data2["iteration"] == 2
    assert data2["verification_passed"] is False
    assert "AssertionError" in data2["verification_errors"]

    # Verify entry 3
    data3 = json.loads(lines[2])
    assert data3["iteration"] == 3
    assert data3["session_status"] == "interrupted"
    assert data3["verification_passed"] is None
