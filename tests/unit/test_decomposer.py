"""Unit tests for TaskDecomposer."""

from pathlib import Path

import pytest

from veridical.orchestrator.decomposer import Subtask, TaskDecomposer


@pytest.fixture
def decomposer() -> TaskDecomposer:
    return TaskDecomposer()


class TestDecomposeNumberedList:
    def test_numbered_list_with_dots(self, decomposer: TaskDecomposer) -> None:
        task = "1. Add login page\n2. Add signup page\n3. Add dashboard"
        result = decomposer.decompose(task)
        assert len(result) == 3
        assert result[0].description == "Add login page"
        assert result[1].description == "Add signup page"
        assert result[2].description == "Add dashboard"

    def test_numbered_list_with_parens(self, decomposer: TaskDecomposer) -> None:
        task = "1) Fix auth\n2) Fix payments"
        result = decomposer.decompose(task)
        assert len(result) == 2
        assert result[0].id == "task-1"
        assert result[1].id == "task-2"

    def test_single_numbered_item_not_split(self, decomposer: TaskDecomposer) -> None:
        task = "1. Just one thing"
        result = decomposer.decompose(task)
        assert len(result) == 1


class TestDecomposeBulletList:
    def test_dash_bullets(self, decomposer: TaskDecomposer) -> None:
        task = "- Add tests\n- Fix linting\n- Update docs"
        result = decomposer.decompose(task)
        assert len(result) == 3
        assert result[0].description == "Add tests"

    def test_asterisk_bullets(self, decomposer: TaskDecomposer) -> None:
        task = "* First task\n* Second task"
        result = decomposer.decompose(task)
        assert len(result) == 2

    def test_single_bullet_not_split(self, decomposer: TaskDecomposer) -> None:
        task = "- Only one item"
        result = decomposer.decompose(task)
        assert len(result) == 1


class TestDecomposeSentenceSplit:
    def test_semicolon_split(self, decomposer: TaskDecomposer) -> None:
        task = "Fix auth; Fix payments; Fix notifications"
        result = decomposer.decompose(task)
        assert len(result) == 3
        assert result[0].description == "Fix auth"

    def test_newline_split(self, decomposer: TaskDecomposer) -> None:
        task = "Fix auth\nFix payments"
        result = decomposer.decompose(task)
        assert len(result) == 2

    def test_single_sentence_returns_one(self, decomposer: TaskDecomposer) -> None:
        task = "Fix the login bug"
        result = decomposer.decompose(task)
        assert len(result) == 1
        assert result[0].description == "Fix the login bug"


class TestDecomposeFromTasksFile:
    def test_unchecked_items(self, decomposer: TaskDecomposer, tmp_path: Path) -> None:
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text(
            "## 1. Implementation\n"
            "- [ ] 1.1 Create schema\n"
            "- [ ] 1.2 Add endpoint\n"
            "- [x] 1.3 Already done\n"
            "- [ ] 1.4 Write tests\n"
        )
        result = decomposer.decompose_from_tasks_file(tasks_file)
        assert len(result) == 3
        assert result[0].description == "1.1 Create schema"
        assert result[1].description == "1.2 Add endpoint"
        assert result[2].description == "1.4 Write tests"

    def test_missing_file(self, decomposer: TaskDecomposer, tmp_path: Path) -> None:
        result = decomposer.decompose_from_tasks_file(tmp_path / "nonexistent.md")
        assert result == []

    def test_empty_file(self, decomposer: TaskDecomposer, tmp_path: Path) -> None:
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("## Nothing here\n")
        result = decomposer.decompose_from_tasks_file(tasks_file)
        assert result == []


class TestSubtaskDataclass:
    def test_defaults(self) -> None:
        st = Subtask(id="t-1", description="Do something")
        assert st.files_hint == []

    def test_with_files_hint(self) -> None:
        st = Subtask(id="t-1", description="Fix auth", files_hint=["src/auth.py"])
        assert st.files_hint == ["src/auth.py"]
