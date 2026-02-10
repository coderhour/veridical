import asyncio
import logging
import time
from pathlib import Path

from veridical.config.schema import QualityGate
from veridical.models.result import GateResult, GateSeverity, GateStatus

logger = logging.getLogger(__name__)


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
        logger.debug(f"Executing command: {gate.command} (timeout: {gate.timeout}s)")

        try:
            # Create subprocess
            # gate.command is validated non-None for 'command' type gates in schema
            assert gate.command is not None
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
                # Handle timeout by killing process and draining pipes to avoid ResourceWarnings
                process.kill()
                try:
                    # communicate() after kill() should be fast as it just drains the pipes
                    _stdout_data, stderr_data = await asyncio.wait_for(
                        process.communicate(), timeout=2.0
                    )
                    error_out = stderr_data.decode("utf-8", errors="replace") if stderr_data else ""
                except (TimeoutError, Exception):
                    # Fallback if communicate still hangs
                    await process.wait()
                    error_out = "Command timed out and failed to drain pipes"

                return GateResult(
                    name=gate.name,
                    command=gate.command,
                    status=GateStatus.ERROR,
                    exit_code=-1,
                    output="",
                    error_output=f"Command timed out after {gate.timeout} seconds. {error_out}",
                    duration_seconds=gate.timeout,
                )

            exit_code = process.returncode or 0
            duration = time.monotonic() - start_time

            # Determine status and severity via exit_code_map or defaults
            status, severity = self._resolve_exit_code(
                exit_code, gate.exit_code_map, gate.warn_only
            )

            logger.debug(f"Command '{gate.name}' finished with exit code {exit_code}")

            return GateResult(
                name=gate.name,
                command=gate.command,
                status=status,
                severity=severity,
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
                severity=GateSeverity.FAIL,
                exit_code=-1,
                output="",
                error_output=str(e),
                duration_seconds=duration,
            )

    @staticmethod
    def _resolve_exit_code(
        exit_code: int,
        exit_code_map: dict[int, str] | None,
        warn_only: bool,
    ) -> tuple[GateStatus, GateSeverity]:
        """Resolve exit code to status and severity.

        Args:
            exit_code: The process exit code.
            exit_code_map: Optional mapping of exit codes to outcomes.
            warn_only: If true, failures become warnings.

        Returns:
            Tuple of (GateStatus, GateSeverity).
        """
        if exit_code_map and exit_code in exit_code_map:
            outcome = exit_code_map[exit_code]
            if outcome == "pass":
                return GateStatus.PASSED, GateSeverity.PASS
            elif outcome == "warn":
                return GateStatus.WARNING, GateSeverity.WARN
            else:  # "fail"
                return GateStatus.FAILED, GateSeverity.FAIL

        # Default behaviour
        if exit_code == 0:
            return GateStatus.PASSED, GateSeverity.PASS

        # Non-zero exit code
        if warn_only:
            return GateStatus.WARNING, GateSeverity.WARN
        return GateStatus.FAILED, GateSeverity.FAIL
