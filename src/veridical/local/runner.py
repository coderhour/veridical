"""Local command runner for Veridical."""

import asyncio
import logging
import os
import subprocess
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from veridical.config.schema import LocalConfig
    from veridical.local.providers.protocol import LocalProvider

logger = logging.getLogger(__name__)


class LocalRunner:
    """Executes the worker command locally."""

    def __init__(
        self,
        config: "LocalConfig",
        console: Console,
        provider: "LocalProvider | None" = None,
        worktree_branch: str | None = None,
    ) -> None:
        """Initialize the local runner.

        Args:
            config: Local configuration
            console: Rich console instance
            provider: Optional local provider for command construction
            worktree_branch: Optional gtr worktree branch name. When set,
                commands are wrapped with ``git gtr run <branch>``.
        """
        self.config = config
        self.console = console
        self.provider = provider
        self.worktree_branch = worktree_branch
        self.last_command: str | None = None

    async def run(
        self,
        error_context: str | None = None,
        task: str | None = None,
    ) -> int:
        """Execute the worker command.

        Args:
            error_context: Optional error context from previous failure
            task: Optional task description (used by provider for command construction)

        Returns:
            Exit code of the command
        """
        mode = self.config.mode

        if self.provider:
            # Use provider's default mode if config doesn't override
            if not self.config.worker_command:
                mode = self.provider.default_mode()
            command = self.provider.build_command(
                task or "Fix the issues",
                error_context,
                mode=mode,
            )
        else:
            command = self.config.worker_command

        if not command:
            self.console.print("[bold red]Error:[/bold red] No worker command specified.")
            return 1

        # Wrap command with gtr run if worktree branch is set
        if self.worktree_branch:
            command = f"git gtr run {self.worktree_branch} {command}"

        env = os.environ.copy()
        # Always pass error context via env var (providers may also embed it in the command)
        if error_context:
            env[self.config.error_env_var] = error_context
            logger.debug(f"Passing error context via {self.config.error_env_var}")

        self.last_command = command
        logger.info(f"Executing worker command: {command}")
        self.console.print(f"[dim]Running worker: {command}[/dim]")

        try:
            if mode == "interactive":
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
