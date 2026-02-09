"""Unit tests for WorkLogWriter class."""

import json
from datetime import datetime
from pathlib import Path

from veridical.worklog.models import WorkLogEntry
from veridical.worklog.writer import WorkLogWriter


def test_worklog_writer_initialization(tmp_path: Path):
    """Test WorkLogWriter initialization with default directory."""
    writer = WorkLogWriter(project_path=tmp_path)

    assert writer.project_path == tmp_path
    assert writer.log_dir == tmp_path / "worklog"
    # Directory should not be created until first write
    assert not writer.log_dir.exists()


def test_worklog_writer_custom_directory(tmp_path: Path):
    """Test WorkLogWriter initialization with custom directory."""
    writer = WorkLogWriter(project_path=tmp_path, log_dir="custom_logs")

    assert writer.log_dir == tmp_path / "custom_logs"
    assert not writer.log_dir.exists()


def test_worklog_writer_write_creates_directory(tmp_path: Path):
    """Test that write() creates the date-based directory structure."""
    writer = WorkLogWriter(project_path=tmp_path)

    entry = WorkLogEntry(
        timestamp=datetime(2026, 2, 6, 15, 30, 0),
        iteration=1,
        session_id="test-session",
        task_description="Test task",
    )

    writer.write(entry)

    # Verify directory structure was created
    expected_dir = tmp_path / "worklog" / "2026-02-06"
    assert expected_dir.exists()
    assert expected_dir.is_dir()


def test_worklog_writer_write_creates_jsonl_file(tmp_path: Path):
    """Test that write() creates iterations.jsonl file."""
    writer = WorkLogWriter(project_path=tmp_path)

    entry = WorkLogEntry(
        timestamp=datetime(2026, 2, 6, 15, 30, 0),
        iteration=1,
        session_id="test-session",
        task_description="Test task",
    )

    writer.write(entry)

    # Verify file was created
    expected_file = tmp_path / "worklog" / "2026-02-06" / "iterations.jsonl"
    assert expected_file.exists()
    assert expected_file.is_file()


def test_worklog_writer_write_appends_entries(tmp_path: Path):
    """Test that multiple entries on the same date are appended."""
    writer = WorkLogWriter(project_path=tmp_path)

    entry1 = WorkLogEntry(
        timestamp=datetime(2026, 2, 6, 10, 0, 0),
        iteration=1,
        session_id="session-1",
        task_description="Task 1",
    )

    entry2 = WorkLogEntry(
        timestamp=datetime(2026, 2, 6, 11, 0, 0),
        iteration=2,
        session_id="session-2",
        task_description="Task 2",
    )

    writer.write(entry1)
    writer.write(entry2)

    # Read the file and verify both entries
    log_file = tmp_path / "worklog" / "2026-02-06" / "iterations.jsonl"
    lines = log_file.read_text().strip().split("\n")

    assert len(lines) == 2

    data1 = json.loads(lines[0])
    assert data1["iteration"] == 1
    assert data1["session_id"] == "session-1"

    data2 = json.loads(lines[1])
    assert data2["iteration"] == 2
    assert data2["session_id"] == "session-2"


def test_worklog_writer_different_dates_separate_files(tmp_path: Path):
    """Test that entries on different dates go to separate files."""
    writer = WorkLogWriter(project_path=tmp_path)

    entry1 = WorkLogEntry(
        timestamp=datetime(2026, 2, 6, 10, 0, 0),
        iteration=1,
        session_id="session-1",
        task_description="Task 1",
    )

    entry2 = WorkLogEntry(
        timestamp=datetime(2026, 2, 7, 10, 0, 0),
        iteration=2,
        session_id="session-2",
        task_description="Task 2",
    )

    writer.write(entry1)
    writer.write(entry2)

    # Verify separate directories and files
    file1 = tmp_path / "worklog" / "2026-02-06" / "iterations.jsonl"
    file2 = tmp_path / "worklog" / "2026-02-07" / "iterations.jsonl"

    assert file1.exists()
    assert file2.exists()

    # Each file should have one entry
    assert len(file1.read_text().strip().split("\n")) == 1
    assert len(file2.read_text().strip().split("\n")) == 1
