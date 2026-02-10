"""Integration tests for local provider CLI features."""

import pytest
from typer.testing import CliRunner

from veridical.cli.main import app

runner = CliRunner()


@pytest.mark.integration
class TestLocalProviderCli:
    """Integration tests for veri local provider options."""

    def test_list_providers(self) -> None:
        """Test 'local --list-providers' displays provider table."""
        result = runner.invoke(app, ["local", "--list-providers"])
        assert result.exit_code == 0
        assert "claude-code" in result.stdout
        assert "gemini-cli" in result.stdout
        assert "Available Local Providers" in result.stdout

    def test_provider_dry_run_claude_code(self) -> None:
        """Test 'local --provider claude-code --dry-run' resolves provider."""
        result = runner.invoke(
            app,
            ["local", "Fix bug", "--provider", "claude-code", "--dry-run", "--no-spec"],
        )
        assert result.exit_code == 0
        assert "Claude Code" in result.stdout
        assert "Dry run" in result.stdout

    def test_provider_dry_run_gemini_cli(self) -> None:
        """Test 'local --provider gemini-cli --dry-run' resolves provider."""
        result = runner.invoke(
            app,
            ["local", "Fix bug", "--provider", "gemini-cli", "--dry-run", "--no-spec"],
        )
        assert result.exit_code == 0
        assert "Gemini" in result.stdout
        assert "Dry run" in result.stdout

    def test_unknown_provider_error(self) -> None:
        """Test 'local --provider unknown' shows error."""
        result = runner.invoke(
            app,
            ["local", "Fix bug", "--provider", "unknown-tool", "--dry-run", "--no-spec"],
        )
        assert result.exit_code == 1
        assert "Unknown local provider" in result.stdout


@pytest.mark.integration
class TestLocalInteractiveFlow:
    """Integration tests for veri local interactive spec selection and task prompt."""

    def test_no_spec_flag_skips_selection(self) -> None:
        """Test 'local --no-spec' skips spec selection entirely."""
        result = runner.invoke(
            app,
            ["local", "Fix bug", "--no-spec", "--dry-run", "--provider", "claude-code"],
        )
        assert result.exit_code == 0
        assert "Select OpenSpec Change" not in result.stdout
        assert "Dry run" in result.stdout

    def test_skip_tasks_alias(self) -> None:
        """Test '--skip-tasks' is an alias for '--no-spec'."""
        result = runner.invoke(
            app,
            ["local", "Fix bug", "--skip-tasks", "--dry-run", "--provider", "claude-code"],
        )
        assert result.exit_code == 0
        assert "Select OpenSpec Change" not in result.stdout

    def test_no_task_empty_input_exits(self) -> None:
        """Test that empty task input at prompt exits with error."""
        result = runner.invoke(
            app,
            ["local", "--no-spec", "--dry-run", "--provider", "claude-code"],
            input="\n",
        )
        assert result.exit_code == 1
        assert "No task description provided" in result.stdout

    def test_no_task_with_input(self) -> None:
        """Test that providing task at prompt proceeds."""
        result = runner.invoke(
            app,
            ["local", "--no-spec", "--dry-run", "--provider", "claude-code"],
            input="Fix the login bug\n",
        )
        assert result.exit_code == 0
        assert "Dry run" in result.stdout
