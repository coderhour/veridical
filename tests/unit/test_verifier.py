"""Tests for the verifier component."""

from pathlib import Path

import pytest

from veridical.models.result import GateStatus
from veridical.verifier.task_completion import verify_task_completion


@pytest.mark.unit
class TestTaskCompletionVerifier:
    """Tests for the task completion verifier."""

    GATE_NAME = "test_gate"

    def test_all_tasks_completed(self, tmp_path: Path) -> None:
        """Test that the gate passes when all tasks are complete."""
        tasks_md = tmp_path / "tasks.md"
        tasks_md.write_text("- [x] Task 1\n- [x] Task 2\n")

        result = verify_task_completion(self.GATE_NAME, tasks_md)
        assert result.status == GateStatus.PASSED
        assert result.name == self.GATE_NAME

    def test_incomplete_tasks(self, tmp_path: Path) -> None:
        """Test that the gate fails when there are incomplete tasks."""
        tasks_md = tmp_path / "tasks.md"
        tasks_md.write_text("- [x] Task 1\n- [ ] Task 2\n- [ ] Task 3\n")

        result = verify_task_completion(self.GATE_NAME, tasks_md)
        assert result.status == GateStatus.FAILED
        assert "Task 2" in result.error_output
        assert "Task 3" in result.error_output

    def test_ignored_incomplete_tasks(self, tmp_path: Path) -> None:
        """Test that incomplete manual/integration tests are ignored."""
        tasks_md = tmp_path / "tasks.md"
        tasks_md.write_text("- [x] Task 1\n- [ ] Some manual test\n- [ ] An integration test\n")

        result = verify_task_completion(self.GATE_NAME, tasks_md)
        assert result.status == GateStatus.PASSED

    def test_mixed_incomplete_tasks(self, tmp_path: Path) -> None:
        """Test a mix of actionable and ignored incomplete tasks."""
        tasks_md = tmp_path / "tasks.md"
        tasks_md.write_text("- [x] Task 1\n- [ ] Actionable task\n- [ ] Some manual test\n")

        result = verify_task_completion(self.GATE_NAME, tasks_md)
        assert result.status == GateStatus.FAILED
        assert "Actionable task" in result.error_output
        assert "manual test" not in result.error_output

    def test_tasks_file_not_found(self, tmp_path: Path) -> None:
        """Test that the gate errors if tasks.md is not found."""
        result = verify_task_completion(self.GATE_NAME, tmp_path / "nonexistent.md")
        assert result.status == GateStatus.ERROR
        assert "File not found" in result.error_output
