"""Local command runner for Veridical."""

import asyncio
import logging
import os
import subprocess
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from veridical.config.schema import LocalConfig

logger = logging.getLogger(__name__)


class LocalRunner:
    """Executes the worker command locally."""

    def __init__(self, config: "LocalConfig", console: Console) -> None:
        """Initialize the local runner.

        Args:
            config: Local configuration
            console: Rich console instance
        """
        self.config = config
        self.console = console

    async def run(self, error_context: str | None = None) -> int:
        """Execute the worker command.

        Args:
            error_context: Optional error context from previous failure

        Returns:
            Exit code of the command
        """
        command = self.config.worker_command
        if not command:
            self.console.print("[bold red]Error:[/bold red] No worker command specified.")
            return 1

        env = os.environ.copy()
        if error_context:
            env[self.config.error_env_var] = error_context
            logger.debug(f"Passing error context via {self.config.error_env_var}")

        logger.info(f"Executing worker command: {command}")
        self.console.print(f"[dim]Running worker: {command}[/dim]")

        try:
            if self.config.mode == "interactive":
                return await self._run_interactive(command, env)
            else:
                return await self._run_subprocess(command, env)
        except Exception as e:
            logger.error(f"Worker execution failed: {e}")
            self.console.print(f"[bold red]Worker execution failed:[/bold red] {e}")
            return 1

    async def _run_interactive(self, command: str, env: dict[str, str]) -> int:
        """Run command interactively (connected to TTY)."""
        # For interactive mode, we use subprocess.run which blocks,
        # but we run it in an executor to avoid blocking the asyncio loop
        loop = asyncio.get_running_loop()

        def _run() -> int:
            result = subprocess.run(
                command,
                shell=True,
                env=env,
                check=False,
            )
            return result.returncode

        return await loop.run_in_executor(None, _run)

    async def _run_subprocess(self, command: str, env: dict[str, str]) -> int:
        """Run command as a subprocess with output capture."""
        process = await asyncio.create_subprocess_shell(
            command,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=self.config.worker_timeout
        )

        if stdout:
            self.console.print(stdout.decode().strip())
        if stderr:
            self.console.print(stderr.decode().strip(), style="red")

        if process.returncode is None:
            # Should not happen after communicate
            return 1

        return process.returncode
