from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

import pytest

from veridical.cli.run import run
from veridical.openspec.scanner import OpenSpecInfo
from veridical.models.result import LoopResult
import typer

@pytest.fixture
def mock_open_specs():
    return [
        OpenSpecInfo(
            name="test-spec",
            path=Path("p1"),
            tasks_file=Path("openspec/changes/test-spec/tasks.md"),
            incomplete_count=1,
            total_count=2,
        )
    ]

@pytest.fixture
def mock_success_result():
    return LoopResult(
        success=True,
        iterations=1,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        final_commit="a1b2c3d",
        target_branch="test-branch",
        failure_reason=None,
        error_context=None,
    )


@pytest.mark.asyncio
async def test_run_with_explicit_spec(mock_open_specs, mock_success_result):
    with patch("veridical.cli.run.find_open_specs", return_value=mock_open_specs), \
         patch("veridical.cli.run.Supervisor") as mock_supervisor, \
         patch("veridical.cli.run.check_spec_status", return_value=MagicMock(needs_attention=False)), \
         patch.dict("os.environ", {"JULES_API_KEY": "dummy_key"}):

        mock_supervisor.return_value.run = AsyncMock(return_value=mock_success_result)
        await run(task="Implement spec test-spec", no_spec=False)

        assert mock_supervisor.called
        instance = mock_supervisor.return_value
        assert instance.run.called

        _args, kwargs = instance.run.call_args
        assert kwargs["tasks_file"] == Path("openspec/changes/test-spec/tasks.md")

@pytest.mark.asyncio
async def test_run_with_no_args_selects_spec(mock_open_specs, mock_success_result):
    with patch("veridical.cli.run.find_open_specs", return_value=mock_open_specs), \
         patch("veridical.cli.run.select_spec", return_value=mock_open_specs[0]), \
         patch("veridical.cli.run.Supervisor") as mock_supervisor, \
         patch("veridical.cli.run.check_spec_status", return_value=MagicMock(needs_attention=False)), \
         patch.dict("os.environ", {"JULES_API_KEY": "dummy_key"}):

        mock_supervisor.return_value.run = AsyncMock(return_value=mock_success_result)
        await run(no_spec=False)

        assert mock_supervisor.called
        instance = mock_supervisor.return_value
        assert instance.run.called

        args, kwargs = instance.run.call_args
        assert args[0] == "Implement spec test-spec"
        assert kwargs["tasks_file"] == Path("openspec/changes/test-spec/tasks.md")

@pytest.mark.asyncio
async def test_run_no_spec_flag(mock_open_specs, mock_success_result):
    with patch("veridical.cli.run.find_open_specs", return_value=mock_open_specs), \
         patch("veridical.cli.run.Supervisor") as mock_supervisor, \
         patch("veridical.cli.run.check_spec_status", return_value=MagicMock(needs_attention=False)), \
         patch.dict("os.environ", {"JULES_API_KEY": "dummy_key"}):

        mock_supervisor.return_value.run = AsyncMock(return_value=mock_success_result)
        await run(task="Some task", no_spec=True)

        assert mock_supervisor.called
        instance = mock_supervisor.return_value
        assert instance.run.called

        _args, kwargs = instance.run.call_args
        assert kwargs["tasks_file"] is None

@pytest.mark.asyncio
async def test_run_no_task_no_specs_error():
    with patch("veridical.cli.run.find_open_specs", return_value=[]), \
         patch("veridical.cli.run.check_spec_status", return_value=MagicMock(needs_attention=False)):

        try:
            await run(no_spec=False)
        except typer.Exit as e:
            assert e.exit_code == 1
        else:
            pytest.fail("typer.Exit was not raised")
