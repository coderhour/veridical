"""Progress reporting using the Rich library."""

import time
from collections.abc import Iterator

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text


class ProgressReporter:
    """Manages Rich live display for polling progress."""

    def __init__(self, console: Console | None = None, verbose: bool = False) -> None:
        self.console = console or Console()
        self.verbose = verbose
        self.live: Live | None = None
        self.start_time: float | None = None
        self.iteration = 0
        self.total_iterations: int | None = None
        self.state: str = "Initializing..."
        self.last_activity: str | None = None
        self.activities: list[str] = []

    def __enter__(self) -> "ProgressReporter":
        """Start the live display."""
        self.start_time = time.time()
        self.live = Live(self._render(), console=self.console, refresh_per_second=10)
        self.live.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Stop the live display."""
        if self.live:
            self.live.stop()
            self.live = None

    def _render(self) -> Panel:
        """Render the progress display."""
        if not self.start_time:
            return Panel("")

        elapsed = time.time() - self.start_time
        elapsed_str = f"{elapsed:.1f}s"

        # Header
        header_table = Table.grid(expand=True)
        header_table.add_column(justify="left")
        header_table.add_column(justify="right")

        spinner = Spinner("dots", text=Text(self.state, style="bold cyan"))
        iteration_str = f"Iteration {self.iteration}"
        if self.total_iterations:
            iteration_str += f"/{self.total_iterations}"

        header_table.add_row(spinner, f"[bold green]{elapsed_str}[/] | [bold]{iteration_str}[/]")

        # Main content
        content_table = Table.grid(padding=(0, 1), expand=True)
        content_table.add_column()
        content_table.add_row(header_table)

        # Last activity summary
        if self.last_activity:
            content_table.add_row(Text(f"• {self.last_activity}", style="yellow"))

        # Verbose activity stream
        if self.verbose and self.activities:
            activity_panel = Panel(
                "\n".join(self.activities),
                title="[bold dim]Activity Stream[/bold dim]",
                border_style="dim",
            )
            content_table.add_row(activity_panel)

        # Combine into a single panel
        main_panel = Panel(
            content_table,
            title="[bold blue]Veridical[/bold blue]",
            subtitle="[dim]Polling for updates...[/dim]",
            border_style="blue",
        )

        return main_panel

    def update(self) -> None:
        """Update the live display with the current state."""
        if self.live:
            self.live.update(self._render())

    def set_state(self, state: str) -> None:
        """Set the current high-level state (e.g., 'Polling')."""
        self.state = state
        self.update()

    def set_iterations(self, current: int, total: int | None = None) -> None:
        """Set the current and total iterations."""
        self.iteration = current
        self.total_iterations = total
        self.update()

    def set_last_activity(self, activity: str) -> None:
        """Set the last activity summary."""
        self.last_activity = activity
        self.update()

    def stream_activity(self, message: str) -> None:
        """Add a message to the verbose activity stream."""
        if self.verbose:
            self.activities.append(message)
            self.update()

    @property
    def is_tty(self) -> bool:
        """Check if running in a TTY context."""
        return self.console.is_terminal


def simple_progress(total: int, description: str = "") -> Iterator[int]:
    """A simple progress indicator for non-TTY environments."""
    for i in range(total):
        print(f"Progress: {i + 1}/{total} - {description}")
        yield i
