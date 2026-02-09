import asyncio
import logging
import os
import shlex
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from veridical.config.schema import LocalConfig

logger = logging.getLogger(__name__)


class LocalRunner:
    """Executes a local command as the AI worker."""

    def __init__(self, config: "LocalConfig") -> None:
        """Initialize the local runner.

        Args:
            config: Local configuration
        """
        self.config = config

    async def run(self, task: str, error_context: str | None = None) -> int:
        """Run the local worker command.

        Args:
            task: The task description to pass to the worker.
            error_context: Optional error context from previous verification.

        Returns:
            The exit code of the worker process.
        """
        env = os.environ.copy()
        if error_context:
            env[self.config.error_env_var] = error_context

        # Construct the command
        # We assume the task is passed as the last argument
        command_str = f"{self.config.worker_command} {shlex.quote(task)}"

        logger.info(f"Running worker: {command_str}")
        logger.debug(f"Error context length: {len(error_context) if error_context else 0}")

        if self.config.mode == "interactive":
            return await self._run_interactive(command_str, env)
        return await self._run_subprocess(command_str, env)

    async def _run_interactive(self, command: str, env: dict[str, str]) -> int:
        """Run the command interactively (foreground)."""

        # Run in a thread to avoid blocking the event loop
        # We use shell=True to allow complex commands
        def _run() -> int:
            try:
                # In interactive mode, we let stdout/stderr flow to the terminal
                # so the user can interact with the tool (e.g., confirm actions)
                result = subprocess.run(
                    command,
                    shell=True,
                    env=env,
                    check=False,
                )
                return result.returncode
            except Exception as e:
                logger.error(f"Interactive worker failed: {e}")
                return 1

        return await asyncio.to_thread(_run)

    async def _run_subprocess(self, command: str, env: dict[str, str]) -> int:
        """Run the command as a subprocess (background)."""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.config.worker_timeout
            )

            if stdout:
                logger.info(f"Worker output:\n{stdout.decode().strip()}")

            if stderr:
                logger.warning(f"Worker stderr:\n{stderr.decode().strip()}")

            return process.returncode or 0

        except TimeoutError:
            logger.error(f"Worker timed out after {self.config.worker_timeout}s")
            try:
                # process might be unbound if create_subprocess_shell fails, but that raises Exception
                # asyncio.create_subprocess_shell returns a Process instance
                process.kill()
                await process.wait()
            except (ProcessLookupError, UnboundLocalError):
                pass
            return -1
        except Exception as e:
            logger.error(f"Subprocess worker failed: {e}")
            return 1
