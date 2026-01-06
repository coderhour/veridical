from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from veridical.supervisor.state_model import LoopState


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """Fixture for a dummy repo root directory."""
    return tmp_path


def test_loop_state_save(repo_root: Path) -> None:
    """Verify that the LoopState model saves to the correct file path."""
    state = LoopState(
        iteration=1,
        session_id="test_session",
        error_context="test_error",
        work_branch="test_branch",
    )

    m_open = mock_open()
    with patch("pathlib.Path.open", m_open):
        state.save(repo_root)

    expected_path = repo_root / ".veridical_state.json"
    m_open.assert_called_once_with("w")


def test_loop_state_load_exists(repo_root: Path) -> None:
    """Verify that the LoopState model loads correctly when the file exists."""
    state_data = {
        "iteration": 1,
        "session_id": "test_session",
        "error_context": "test_error",
        "work_branch": "test_branch",
    }
    state_json = '{"iteration": 1, "session_id": "test_session", "error_context": "test_error", "work_branch": "test_branch"}'

    m_open = mock_open(read_data=state_json)
    with patch("pathlib.Path.open", m_open), patch(
        "pathlib.Path.exists", return_value=True
    ):
        state = LoopState.load(repo_root)

    assert state is not None
    assert state.iteration == state_data["iteration"]
    assert state.session_id == state_data["session_id"]
    assert state.error_context == state_data["error_context"]
    assert state.work_branch == state_data["work_branch"]


def test_loop_state_load_not_exists(repo_root: Path) -> None:
    """Verify that loading returns None when the state file does not exist."""
    with patch("pathlib.Path.exists", return_value=False):
        state = LoopState.load(repo_root)

    assert state is None


def test_loop_state_clear_exists(repo_root: Path) -> None:
    """Verify that the state file is cleared if it exists."""
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.unlink"
    ) as m_unlink:
        LoopState.clear(repo_root)
        m_unlink.assert_called_once()


def test_loop_state_clear_not_exists(repo_root: Path) -> None:
    """Verify that clear does not fail if the file does not exist."""
    with patch("pathlib.Path.exists", return_value=False), patch(
        "pathlib.Path.unlink"
    ) as m_unlink:
        LoopState.clear(repo_root)
        m_unlink.assert_not_called()
