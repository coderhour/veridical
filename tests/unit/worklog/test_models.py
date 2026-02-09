"""Unit tests for WorkLogEntry model."""

import json
from datetime import datetime

from veridical.worklog.models import WorkLogEntry


def test_work_log_entry_creation():
    """Test creating a WorkLogEntry with required fields."""
    entry = WorkLogEntry(
        iteration=1,
        session_id="test-session-123",
        task_description="Fix bug in module X",
    )

    assert entry.iteration == 1
    assert entry.session_id == "test-session-123"
    assert entry.task_description == "Fix bug in module X"
    assert isinstance(entry.timestamp, datetime)
    assert entry.error_context is None
    assert entry.prompt_sent is None
    assert entry.session_status == "unknown"
    assert entry.verification_passed is None
    assert entry.verification_errors is None
    assert entry.duration_seconds is None


def test_work_log_entry_with_all_fields():
    """Test creating a WorkLogEntry with all fields populated."""
    timestamp = datetime(2026, 2, 6, 15, 30, 0)
    entry = WorkLogEntry(
        timestamp=timestamp,
        iteration=2,
        session_id="test-session-456",
        task_description="Implement feature Y",
        error_context="Previous test failed",
        prompt_sent="Fix the failing test",
        session_status="completed",
        verification_passed=True,
        verification_errors=None,
        duration_seconds=120.5,
    )

    assert entry.timestamp == timestamp
    assert entry.iteration == 2
    assert entry.session_id == "test-session-456"
    assert entry.task_description == "Implement feature Y"
    assert entry.error_context == "Previous test failed"
    assert entry.prompt_sent == "Fix the failing test"
    assert entry.session_status == "completed"
    assert entry.verification_passed is True
    assert entry.verification_errors is None
    assert entry.duration_seconds == 120.5


def test_work_log_entry_serialization():
    """Test that WorkLogEntry can be serialized to JSON."""
    entry = WorkLogEntry(
        iteration=1,
        session_id="test-session-789",
        task_description="Test serialization",
        session_status="completed",
        verification_passed=False,
        verification_errors="Test failed: assertion error",
        duration_seconds=45.2,
    )

    json_str = entry.model_dump_json()
    assert isinstance(json_str, str)

    # Verify it's valid JSON
    data = json.loads(json_str)
    assert data["iteration"] == 1
    assert data["session_id"] == "test-session-789"
    assert data["task_description"] == "Test serialization"
    assert data["session_status"] == "completed"
    assert data["verification_passed"] is False
    assert data["verification_errors"] == "Test failed: assertion error"
    assert data["duration_seconds"] == 45.2
