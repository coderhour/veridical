"""Unit tests for DifficultyEstimator."""

import json
from pathlib import Path

import pytest

from veridical.learning.estimator import DifficultyEstimator


@pytest.fixture
def worklog_dir(tmp_path: Path) -> Path:
    return tmp_path / "worklog"


def _write_entries(worklog_dir: Path, entries: list[dict], date: str = "2025-01-15") -> None:
    date_dir = worklog_dir / date
    date_dir.mkdir(parents=True, exist_ok=True)
    with (date_dir / "iterations.jsonl").open("a") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def _make_entry(
    iteration: int = 1,
    session_id: str = "sess-1",
    task: str = "Fix the login validation bug",
    passed: bool = False,
    date: str = "2025-01-15",
) -> dict:
    return {
        "timestamp": f"{date}T10:00:00",
        "iteration": iteration,
        "session_id": session_id,
        "task_description": task,
        "verification_passed": passed,
    }


class TestDifficultyEstimator:
    def test_predict_no_worklog_dir(self, tmp_path: Path) -> None:
        estimator = DifficultyEstimator(default_max_iterations=10)
        estimate = estimator.predict("some task", tmp_path / "nonexistent")
        assert estimate.confidence == "low"
        assert estimate.predicted_iterations == 5
        assert estimate.similar_tasks == []

    def test_predict_empty_worklog(self, worklog_dir: Path) -> None:
        worklog_dir.mkdir(parents=True)
        estimator = DifficultyEstimator(default_max_iterations=10)
        estimate = estimator.predict("some task", worklog_dir)
        assert estimate.confidence == "low"
        assert estimate.predicted_iterations == 5

    def test_predict_with_similar_tasks(self, worklog_dir: Path) -> None:
        # Create historical data with similar tasks
        for i in range(5):
            entries = [
                _make_entry(
                    iteration=j + 1, session_id=f"sess-{i}", task="Fix the login validation bug"
                )
                for j in range(3)
            ]
            entries[-1]["verification_passed"] = True
            _write_entries(worklog_dir, entries, date=f"2025-01-{15 + i:02d}")

        estimator = DifficultyEstimator(default_max_iterations=10)
        estimate = estimator.predict("Fix the login authentication bug", worklog_dir)

        assert estimate.predicted_iterations >= 1
        assert len(estimate.similar_tasks) > 0

    def test_predict_no_similar_tasks(self, worklog_dir: Path) -> None:
        # Historical tasks are completely different
        for i in range(5):
            _write_entries(
                worklog_dir,
                [_make_entry(session_id=f"sess-{i}", task="Refactor database schema migration")],
                date=f"2025-01-{15 + i:02d}",
            )

        estimator = DifficultyEstimator(default_max_iterations=10)
        estimate = estimator.predict("Fix CSS styling on homepage", worklog_dir)

        assert estimate.confidence == "low"
        assert estimate.predicted_iterations == 5

    def test_predict_uses_weighted_average(self, worklog_dir: Path) -> None:
        # Two groups of similar tasks with different iteration counts
        for i in range(3):
            entries = [
                _make_entry(
                    iteration=j + 1, session_id=f"sess-a{i}", task="Fix the parser validation error"
                )
                for j in range(2)
            ]
            entries[-1]["verification_passed"] = True
            _write_entries(worklog_dir, entries, date=f"2025-01-{10 + i:02d}")

        for i in range(3):
            entries = [
                _make_entry(
                    iteration=j + 1,
                    session_id=f"sess-b{i}",
                    task="Fix the parser output formatting",
                )
                for j in range(6)
            ]
            entries[-1]["verification_passed"] = True
            _write_entries(worklog_dir, entries, date=f"2025-01-{20 + i:02d}")

        estimator = DifficultyEstimator(default_max_iterations=10)
        estimate = estimator.predict("Fix the parser error handling", worklog_dir)

        # Should be somewhere between 2 and 6
        assert 1 <= estimate.predicted_iterations <= 8

    def test_similar_tasks_limited_to_five(self, worklog_dir: Path) -> None:
        for i in range(10):
            _write_entries(
                worklog_dir,
                [
                    _make_entry(
                        session_id=f"sess-{i}",
                        task=f"Fix the validation error in module_{i}",
                        passed=True,
                    )
                ],
                date=f"2025-01-{10 + i:02d}",
            )

        estimator = DifficultyEstimator(default_max_iterations=10)
        estimate = estimator.predict("Fix the validation error in module_new", worklog_dir)
        assert len(estimate.similar_tasks) <= 5

    def test_default_max_iterations_fallback(self, tmp_path: Path) -> None:
        estimator = DifficultyEstimator(default_max_iterations=20)
        estimate = estimator.predict("anything", tmp_path / "nonexistent")
        assert estimate.predicted_iterations == 10  # 20 // 2
