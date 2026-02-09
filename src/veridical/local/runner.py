import asyncio
import logging
import os
import shlex
import subprocess
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from veridical.config.schema import LocalConfig

logger = logging.getLogger(__name__)


class LocalRunner:
    """Executes the local worker command."""

    def __init__(self, config: "LocalConfig", console: Console | None = None) -> None:
        """Initialize the local runner.

        Args:
            config: Local configuration
            console: Rich console instance
        """
        self.config = config
        self.console = console or Console()

    async def run(self, error_context: str | None = None) -> int:
        """Execute the worker command.

        Args:
            error_context: Optional error context from previous verification failure.

        Returns:
            Exit code of the command.
        """
        command = self.config.worker_command
        if not command:
            logger.warning("No worker command configured.")
            return 0

        logger.info(f"Running worker command: {command}")

        # Prepare environment
        env = os.environ.copy()
        if error_context:
            env[self.config.error_env_var] = error_context
            logger.debug(f"Passing error context via {self.config.error_env_var}")

        try:
            if self.config.mode == "interactive":
                return await self._run_interactive(command, env)
            else:
                return await self._run_subprocess(command, env)
        except Exception as e:
            logger.error(f"Failed to execute worker command: {e}")
            self.console.print(f"[bold red]Error running worker:[/bold red] {e}")
            return 1

    async def _run_interactive(self, command: str, env: dict[str, str]) -> int:
        """Run command in interactive mode (foreground)."""
        logger.info("Starting interactive worker session...")

        # We use asyncio.to_thread to run the blocking subprocess call
        # in a separate thread, keeping the event loop alive.
        # However, for true interactive TTY access, simple subprocess.call/run works best.
        # Since we are blocking the supervisor anyway, blocking the loop is acceptable here
        # IF we don't have other concurrent tasks. The Supervisor is sequential.

        # Using synchronous subprocess.run to ensure TTY handling is correct
        def _execute():
            # shell=True to allow complex commands
            return subprocess.run(
                command,
                shell=True,
                env=env,
                check=False
            ).returncode

        return await asyncio.to_thread(_execute)

    async def _run_subprocess(self, command: str, env: dict[str, str]) -> int:
        """Run command in subprocess mode (captured output)."""
        logger.info("Starting worker subprocess...")

        process = await asyncio.create_subprocess_shell(
            command,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.worker_timeout
            )

            if stdout:
                logger.info(f"Worker stdout:\n{stdout.decode(errors='replace').strip()}")
            if stderr:
                logger.warning(f"Worker stderr:\n{stderr.decode(errors='replace').strip()}")

            return process.returncode or 0

        except asyncio.TimeoutError:
            logger.error(f"Worker command timed out after {self.config.worker_timeout}s")
            try:
                process.kill()
                await process.wait()
            except ProcessLookupError:
                pass
            return 124  # Standard timeout exit code
