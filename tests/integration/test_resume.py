from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer import Exit

from veridical.cli.resume import resume
from veridical.models.result import LoopResult
from veridical.supervisor.loop import Supervisor
from veridical.supervisor.state_model import LoopState


@pytest.mark.asyncio
async def test_resume_loads_state(tmp_path: Path, mocker) -> None:
    """Test that the resume command correctly loads the state file."""
    repo_path = tmp_path
    state_file = LoopState.get_state_file_path(repo_path)

    # Initialize a git repository
    import subprocess
    subprocess.run(["git", "init"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)
    (repo_path / "README.md").write_text("init")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_path, check=True)

    # Create a dummy state file
    state = LoopState(task_description="Test task")
    state.save(repo_path)

    # Mock Supervisor.run to return a successful result
    mock_result = LoopResult(
        success=True,
        iterations=1,
        duration_seconds=10.0,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        final_commit="a1b2c3d",
        target_branch="test-branch",
        failure_reason=None,
        error_context=None,
    )
    mock_supervisor_run = mocker.patch.object(
        Supervisor, "run", autospec=True, return_value=mock_result
    )
    mocker.patch("veridical.supervisor.loop.JulesClient")
    mocker.patch("os.environ", new={"JULES_API_KEY": "dummy_key"})
    mocker.patch("pathlib.Path.cwd", return_value=repo_path)
    mocker.patch("veridical.cli.run.select_spec", return_value=None)

    await resume(
        config_path=None,
        verbose=False,
        dry_run=False,
    )

    mock_supervisor_run.assert_called_once()
    call_args = mock_supervisor_run.call_args
    # The 'task' argument is the second positional argument to Supervisor.run (after self)
    assert call_args.args[1] == "Test task"
