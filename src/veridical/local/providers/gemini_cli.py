"""Gemini CLI provider for Veridical local loop."""

import shlex
import shutil
from typing import Literal


class GeminiCliProvider:
    """Provider preset for Google's Gemini CLI.

    Configures the local runner to use the ``gemini`` CLI with
    appropriate flags for subprocess and interactive modes.

    Subprocess mode uses ``gemini -p`` with error context appended
    to the prompt text. Interactive mode launches bare ``gemini``
    with error context delivered via environment variable.
    """

    @property
    def name(self) -> str:
        """Short identifier for the provider."""
        return "gemini-cli"

    @property
    def description(self) -> str:
        """Human-readable description."""
        return "Google Gemini CLI (gemini)"

    def build_command(
        self,
        task: str,
        error_context: str | None = None,
        *,
        mode: Literal["interactive", "subprocess"] = "subprocess",
    ) -> str:
        """Construct the gemini CLI command.

        Args:
            task: Task description / prompt
            error_context: Error feedback from the previous iteration
            mode: Execution mode

        Returns:
            Shell command string
        """
        if mode == "interactive":
            return "gemini"

        # Subprocess mode: pass prompt via -p flag
        prompt = task
        if error_context:
            prompt = f"{task}\n\nPrevious verification failed. Fix these errors:\n{error_context}"

        return f"gemini -p {shlex.quote(prompt)}"

    def default_mode(self) -> Literal["interactive", "subprocess"]:
        """Gemini CLI defaults to subprocess mode."""
        return "subprocess"

    def detect(self) -> bool:
        """Check if gemini CLI is available on PATH."""
        return shutil.which("gemini") is not None
