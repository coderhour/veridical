"""Claude Code provider for Veridical local loop."""

import shlex
import shutil
from typing import Literal


class ClaudeCodeProvider:
    """Provider preset for Anthropic's Claude Code CLI.

    Configures the local runner to use the ``claude`` CLI with
    appropriate flags for subprocess and interactive modes.

    Subprocess mode uses ``claude --print --output-format text -p``
    with ``--append-system-prompt`` for error context delivery.
    Interactive mode launches bare ``claude`` with error context
    delivered via environment variable.
    """

    @property
    def name(self) -> str:
        """Short identifier for the provider."""
        return "claude-code"

    @property
    def description(self) -> str:
        """Human-readable description."""
        return "Anthropic Claude Code CLI (claude)"

    def build_command(
        self,
        task: str,
        error_context: str | None = None,
        *,
        mode: Literal["interactive", "subprocess"] = "subprocess",
    ) -> str:
        """Construct the claude CLI command.

        Args:
            task: Task description / prompt
            error_context: Error feedback from the previous iteration
            mode: Execution mode

        Returns:
            Shell command string
        """
        if mode == "interactive":
            return "claude"

        # Subprocess mode: use --print for non-interactive output
        parts = ["claude", "--print", "--output-format", "text", "-p", shlex.quote(task)]

        if error_context:
            parts.extend(
                [
                    "--append-system-prompt",
                    shlex.quote(
                        f"Previous verification failed. Fix these errors:\n{error_context}"
                    ),
                ]
            )

        return " ".join(parts)

    def default_mode(self) -> Literal["interactive", "subprocess"]:
        """Claude Code defaults to subprocess mode."""
        return "subprocess"

    def detect(self) -> bool:
        """Check if claude CLI is available on PATH."""
        return shutil.which("claude") is not None
