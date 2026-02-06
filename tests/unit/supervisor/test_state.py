from pathlib import Path

from veridical.supervisor.state import LoopState


def test_loop_state_serialization(tmp_path: Path) -> None:
    """Test saving and loading loop state."""
    state = LoopState(
        task_description="test task",
        iteration=1,
        session_id="sess-123",
        work_branch="feat/test",
        error_context="some error",
        started_at_timestamp=1000.0,
    )

    state_file = tmp_path / "state.json"
    state.save(state_file)

    assert state_file.exists()

    loaded = LoopState.load(state_file)
    assert loaded == state
    assert loaded.iteration == 1
    assert loaded.session_id == "sess-123"
    assert loaded.work_branch == "feat/test"
