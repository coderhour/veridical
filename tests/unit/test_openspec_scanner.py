
import pytest

from veridical.openspec.scanner import find_open_specs


@pytest.fixture
def mock_openspec_dir(tmp_path):
    # Create a mock openspec structure
    changes_dir = tmp_path / "openspec" / "changes"
    changes_dir.mkdir(parents=True)

    # Spec 1: All tasks complete
    spec1 = changes_dir / "spec-complete"
    spec1.mkdir()
    (spec1 / "tasks.md").write_text("- [x] Task 1\n- [x] Task 2")

    # Spec 2: Some tasks incomplete
    spec2 = changes_dir / "spec-incomplete"
    spec2.mkdir()
    (spec2 / "tasks.md").write_text("- [x] Task 1\n- [ ] Task 2\n- [ ] Task 3")

    # Spec 3: No tasks file (should be ignored)
    spec3 = changes_dir / "spec-no-tasks"
    spec3.mkdir()

    return changes_dir


def test_find_open_specs(mock_openspec_dir):
    specs = find_open_specs(mock_openspec_dir)

    assert len(specs) == 1
    assert specs[0].name == "spec-incomplete"
    assert specs[0].incomplete_count == 2
    assert specs[0].total_count == 3
    assert specs[0].tasks_file.name == "tasks.md"


def test_find_open_specs_empty(tmp_path):
    specs = find_open_specs(tmp_path / "nonexistent")
    assert specs == []


def test_find_open_specs_no_incomplete(tmp_path):
    changes_dir = tmp_path / "changes"
    changes_dir.mkdir()
    spec = changes_dir / "all-done"
    spec.mkdir()
    (spec / "tasks.md").write_text("- [x] Done")

    specs = find_open_specs(changes_dir)
    assert specs == []
