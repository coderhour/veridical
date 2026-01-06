"""Tests for CLI session resume option."""

import pytest
from typer.testing import CliRunner

from veridical.cli.main import app

runner = CliRunner()


@pytest.mark.unit
class TestCLISessionResume:
    """Tests for CLI --session-id option."""

    def test_session_id_long_option_accepted(self) -> None:
        """Test that --session-id option is accepted."""
        # Note: This will fail due to missing API key, but we're just testing
        # that the option is parsed correctly
        result = runner.invoke(
            app,
            ["run", "Test task", "--session-id", "test-session-123", "--dry-run"],
        )
        # Should not fail with "no such option" error
        assert "no such option" not in result.stdout.lower()

    def test_session_id_short_option_accepted(self) -> None:
        """Test that -s shortcut is accepted."""
        result = runner.invoke(
            app,
            ["run", "Test task", "-s", "test-session-123", "--dry-run"],
        )
        # Should not fail with "no such option" error
        assert "no such option" not in result.stdout.lower()

    def test_run_without_session_id_works(self) -> None:
        """Test that run command works without session ID (normal flow)."""
        result = runner.invoke(
            app,
            ["run", "Test task", "--dry-run"],
        )
        # Should not fail with option errors
        assert "no such option" not in result.stdout.lower()
