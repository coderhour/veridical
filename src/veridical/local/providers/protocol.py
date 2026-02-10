"""LocalProvider protocol definition using structural subtyping."""

from typing import Literal, Protocol, runtime_checkable


@runtime_checkable
class LocalProvider(Protocol):
    """Protocol for local AI coding tool provider presets.

    Any class implementing these methods with matching signatures
    satisfies this protocol via structural subtyping — no inheritance
    required.

    A LocalProvider encapsulates tool-specific knowledge: how to
    construct the CLI command, which execution mode to use, and
    how to detect whether the tool is installed.
    """

    @property
    def name(self) -> str:
        """Short identifier for the provider (e.g., 'claude-code')."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description of the provider."""
        ...

    def build_command(
        self,
        task: str,
        error_context: str | None = None,
        *,
        mode: Literal["interactive", "subprocess"] = "subprocess",
    ) -> str:
        """Construct the shell command for the given task.

        Args:
            task: Task description / prompt
            error_context: Error feedback from the previous iteration
            mode: Execution mode (interactive or subprocess)

        Returns:
            Shell command string ready for execution
        """
        ...

    def default_mode(self) -> Literal["interactive", "subprocess"]:
        """Return the preferred execution mode for this provider."""
        ...

    def detect(self) -> bool:
        """Check if the tool is available on PATH.

        Returns:
            True if the tool binary is found, False otherwise
        """
        ...
