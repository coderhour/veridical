from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from veridical.cli.main import app

runner = CliRunner()


@pytest.fixture
def mock_open_specs():
    from veridical.openspec.scanner import OpenSpecInfo

    return [
        OpenSpecInfo(
            name="test-spec",
            path=Path("p1"),
            tasks_file=Path("openspec/changes/test-spec/tasks.md"),
            incomplete_count=1,
            total_count=2,
        )
    ]


def test_run_with_explicit_spec(mock_open_specs):
    # Mock find_open_specs to return our test spec
    with (
        patch("veridical.cli.run.find_open_specs", return_value=mock_open_specs),
        patch("veridical.cli.run.run_supervisor") as mock_run_supervisor,
        patch("veridical.cli.run.check_spec_status") as mock_check_spec,
        patch("pathlib.Path.exists", return_value=False),
    ):
        mock_check_spec.return_value.needs_attention = False

        result = runner.invoke(app, ["run", "Implement spec test-spec", "--dry-run"])

        assert result.exit_code == 0
        mock_run_supervisor.assert_called_once()
        _args, kwargs = mock_run_supervisor.call_args
        assert kwargs["tasks_file"] == Path("openspec/changes/test-spec/tasks.md")


def test_run_with_no_args_selects_spec(mock_open_specs):
    # Mock find_open_specs and select_spec
    with (
        patch("veridical.cli.run.find_open_specs", return_value=mock_open_specs),
        patch("veridical.cli.run.select_spec", return_value=mock_open_specs[0]),
        patch("veridical.cli.run.run_supervisor") as mock_run_supervisor,
        patch("veridical.cli.run.check_spec_status") as mock_check_spec,
        patch("pathlib.Path.exists", return_value=False),
    ):
        mock_check_spec.return_value.needs_attention = False

        result = runner.invoke(app, ["run", "--dry-run"])

        assert result.exit_code == 0
        mock_run_supervisor.assert_called_once()
        args, kwargs = mock_run_supervisor.call_args
        assert args[0] == "Implement spec test-spec"
        assert kwargs["tasks_file"] == Path("openspec/changes/test-spec/tasks.md")


def test_run_no_spec_flag(mock_open_specs):
    with (
        patch("veridical.cli.run.find_open_specs", return_value=mock_open_specs),
        patch("veridical.cli.run.run_supervisor") as mock_run_supervisor,
        patch("veridical.cli.run.check_spec_status") as mock_check_spec,
        patch("pathlib.Path.exists", return_value=False),
    ):
        mock_check_spec.return_value.needs_attention = False

        result = runner.invoke(app, ["run", "Some task", "--no-spec", "--dry-run"])

        assert result.exit_code == 0
        mock_run_supervisor.assert_called_once()
        _args, kwargs = mock_run_supervisor.call_args
        assert kwargs["tasks_file"] is None


def test_run_no_task_no_specs_error():
    with (
        patch("veridical.cli.run.find_open_specs", return_value=[]),
        patch("veridical.cli.run.check_spec_status") as mock_check_spec,
        patch("pathlib.Path.exists", return_value=False),
    ):
        mock_check_spec.return_value.needs_attention = False

        result = runner.invoke(app, ["run"])

        assert result.exit_code == 1
        assert "No task description provided and no spec selected" in result.stdout
