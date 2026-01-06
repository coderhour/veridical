"""Unit tests for the ProgressReporter class."""

from unittest.mock import MagicMock

from rich.console import Console

from veridical.ui.progress import ProgressReporter


def test_progress_reporter_initialization() -> None:
    """Test that ProgressReporter initializes correctly."""
    console = Console(file=MagicMock())
    reporter = ProgressReporter(console=console, verbose=True)
    assert reporter.console == console
    assert reporter.verbose is True
    assert reporter.state == "Initializing..."


def test_progress_reporter_lifecycle() -> None:
    """Test the enter and exit methods of the reporter."""
    console = Console(file=MagicMock())
    reporter = ProgressReporter(console=console)

    with reporter as r:
        assert r.live is not None
        assert r.start_time is not None
    assert reporter.live is None


def test_progress_reporter_set_state() -> None:
    """Test that set_state updates the reporter's state."""
    console = Console(file=MagicMock())
    reporter = ProgressReporter(console=console)
    with reporter:
        reporter.set_state("Testing...")
        assert reporter.state == "Testing..."


def test_progress_reporter_set_iterations() -> None:
    """Test that set_iterations updates the iteration count."""
    console = Console(file=MagicMock())
    reporter = ProgressReporter(console=console)
    with reporter:
        reporter.set_iterations(5, 10)
        assert reporter.iteration == 5
        assert reporter.total_iterations == 10


def test_progress_reporter_stream_activity_verbose() -> None:
    """Test that stream_activity adds to activities in verbose mode."""
    console = Console(file=MagicMock())
    reporter = ProgressReporter(console=console, verbose=True)
    with reporter:
        reporter.stream_activity("New activity")
        assert "New activity" in reporter.activities


def test_progress_reporter_stream_activity_non_verbose() -> None:
    """Test that stream_activity does nothing in non-verbose mode."""
    console = Console(file=MagicMock())
    reporter = ProgressReporter(console=console, verbose=False)
    with reporter:
        reporter.stream_activity("New activity")
        assert not reporter.activities


def test_progress_reporter_render_output() -> None:
    """Test the _render method to ensure it produces a renderable."""
    console = Console(file=MagicMock(), force_terminal=True)
    reporter = ProgressReporter(console=console, verbose=True)
    with reporter as r:
        r.set_state("Rendering...")
        r.set_iterations(1, 5)
        r.set_last_activity("Last thing")
        r.stream_activity("Stream thing")
        renderable = r._render()
        # Use Rich's built-in method to get console renderables
        with console.capture() as capture:
            console.print(renderable)
        text = capture.get()
        # Strip ANSI escape codes for robust assertion
        import re

        text = re.sub(r"\x1b\[[0-9;]*[mK]", "", text)
        assert "Rendering..." in text
        assert "1/5" in text
        assert "Last thing" in text
        assert "Stream thing" in text


def test_progress_reporter_is_tty() -> None:
    """Test the is_tty property."""
    # Test with a TTY
    tty_console = Console(file=MagicMock(), force_terminal=True)
    tty_reporter = ProgressReporter(console=tty_console)
    assert tty_reporter.is_tty is True

    # Test with a non-TTY
    non_tty_console = Console(file=MagicMock(), force_terminal=False)
    non_tty_reporter = ProgressReporter(console=non_tty_console)
    assert non_tty_reporter.is_tty is False
