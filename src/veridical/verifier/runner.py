"""Command execution for quality gates."""

import asyncio
import time
from pathlib import Path

from veridical.config.schema import QualityGate
from veridical.models.result import GateResult, GateStatus


class CommandRunner:
    """Executes quality gate commands and captures output."""

    def __init__(self, repo_path: Path) -> None:
        """Initialize the command runner.

        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = repo_path

    async def run_gate(self, gate: QualityGate) -> GateResult:
        """Run a single quality gate command.

        Args:
            gate: Quality gate configuration

        Returns:
            Result of running the gate
        """
        start_time = time.monotonic()

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                gate.command,
                cwd=self.repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=gate.timeout,
                )
            except TimeoutError:
                process.kill()
                await process.wait()
                return GateResult(
                    name=gate.name,
                    command=gate.command,
                    status=GateStatus.ERROR,
                    exit_code=-1,
                    output="",
                    error_output=f"Command timed out after {gate.timeout} seconds",
                    duration_seconds=gate.timeout,
                )

            exit_code = process.returncode or 0
            duration = time.monotonic() - start_time

            # Determine status
            status = GateStatus.PASSED if exit_code == 0 else GateStatus.FAILED

            return GateResult(
                name=gate.name,
                command=gate.command,
                status=status,
                exit_code=exit_code,
                output=stdout.decode("utf-8", errors="replace"),
                error_output=stderr.decode("utf-8", errors="replace"),
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.monotonic() - start_time
            return GateResult(
                name=gate.name,
                command=gate.command,
                status=GateStatus.ERROR,
                exit_code=-1,
                output="",
                error_output=str(e),
                duration_seconds=duration,
            )
