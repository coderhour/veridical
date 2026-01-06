from pathlib import Path

from veridical.supervisor.state_model import LoopState


def test_loop_state_save_load_clear(tmp_path: Path) -> None:
    """Test saving, loading, and clearing LoopState."""
    repo_path = tmp_path
    state_file = LoopState.get_state_file_path(repo_path)

    # 1. Initial state: No file exists
    assert not state_file.exists()
    loaded_state = LoopState.load(repo_path)
    assert loaded_state is None

    # 2. Save a state
    state = LoopState(
        task_description="Fix all the bugs",
        tasks_file="path/to/tasks.md",
        iteration=3,
        session_id="abc-123",
        error_context="Something went wrong",
        work_branch="feature/fix-bugs",
    )
    state.save(repo_path)
    assert state_file.exists()

    # 3. Load the state
    loaded_state = LoopState.load(repo_path)
    assert loaded_state is not None
    assert loaded_state.task_description == "Fix all the bugs"
    assert loaded_state.tasks_file == "path/to/tasks.md"
    assert loaded_state.iteration == 3
    assert loaded_state.session_id == "abc-123"
    assert loaded_state.error_context == "Something went wrong"
    assert loaded_state.work_branch == "feature/fix-bugs"

    # 4. Clear the state
    LoopState.clear(repo_path)
    assert not state_file.exists()


def test_load_corrupted_state_file(tmp_path: Path) -> None:
    """Test that loading a corrupted state file returns None and clears the file."""
    repo_path = tmp_path
    state_file = LoopState.get_state_file_path(repo_path)

    # Create a corrupted JSON file
    state_file.write_text("{'invalid_json': True,}")

    assert state_file.exists()

    # Try to load it
    loaded_state = LoopState.load(repo_path)
    assert loaded_state is None

    # Check that the corrupted file was cleared
    assert not state_file.exists()
