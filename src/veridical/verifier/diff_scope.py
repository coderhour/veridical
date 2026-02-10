"""Diff scope gate runner for verifying modified files against allowed patterns."""

import logging
import time
from pathlib import Path

from veridical.config.schema import QualityGate
from veridical.models.result import GateResult, GateSeverity, GateStatus
from veridical.verifier.glob_match import glob_match

logger = logging.getLogger(__name__)


class DiffScopeGateRunner:
    """Runs diff scope gates that check modified files against allowed glob patterns."""

    def __init__(self, repo_path: Path) -> None:
        """Initialize the diff scope gate runner.

        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = repo_path

    def run_gate(self, gate: QualityGate, changed_files: list[str]) -> GateResult:
        """Run a diff scope gate.

        Args:
            gate: Quality gate configuration with allowed_patterns
            changed_files: List of file paths modified in the current iteration

        Returns:
            Result of running the diff scope gate
        """
        start_time = time.monotonic()
        assert gate.allowed_patterns is not None

        # No changes means pass
        if not changed_files:
            return GateResult(
                name=gate.name,
                status=GateStatus.PASSED,
                severity=GateSeverity.PASS,
                output="No files were modified",
                duration_seconds=time.monotonic() - start_time,
            )

        disallowed: list[str] = []
        for file_path in changed_files:
            if not any(glob_match(file_path, pattern) for pattern in gate.allowed_patterns):
                disallowed.append(file_path)

        duration = time.monotonic() - start_time

        if disallowed:
            severity = GateSeverity.WARN if gate.warn_only else GateSeverity.FAIL
            status = GateStatus.WARNING if gate.warn_only else GateStatus.FAILED
            error_msg = "Files modified outside allowed scope:\n" + "\n".join(
                f"  - {f}" for f in disallowed
            )
            return GateResult(
                name=gate.name,
                status=status,
                severity=severity,
                error_output=error_msg,
                duration_seconds=duration,
            )

        return GateResult(
            name=gate.name,
            status=GateStatus.PASSED,
            severity=GateSeverity.PASS,
            output=f"All {len(changed_files)} modified files match allowed patterns",
            duration_seconds=duration,
        )
