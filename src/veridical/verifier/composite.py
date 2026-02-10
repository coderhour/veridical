"""Composite gate runner for grouping sub-gates with logical operators."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from veridical.models.result import GateResult, GateSeverity, GateStatus

if TYPE_CHECKING:
    from veridical.config.schema import QualityGate
    from veridical.verifier.quality_gate import Verifier

logger = logging.getLogger(__name__)


class CompositeGateRunner:
    """Runs composite gates that group sub-gates with all_of (AND) or any_of (OR) logic."""

    def __init__(self, verifier: Verifier) -> None:
        """Initialize the composite gate runner.

        Args:
            verifier: The parent Verifier instance, used to dispatch sub-gates
        """
        self.verifier = verifier

    async def run_gate(self, gate: QualityGate) -> GateResult:
        """Run a composite gate.

        Args:
            gate: Quality gate configuration with mode and sub-gates

        Returns:
            Aggregated result of running all sub-gates
        """
        start_time = time.monotonic()
        assert gate.mode is not None
        assert gate.gates is not None

        sub_results: list[GateResult] = []
        for sub_gate in gate.gates:
            result = await self.verifier._run_gate_logic(sub_gate)
            sub_results.append(result)

            # Early exit for all_of: stop on first failure
            if gate.mode == "all_of" and not result.passed:
                break

            # Early exit for any_of: stop on first pass
            if gate.mode == "any_of" and result.passed:
                break

        duration = time.monotonic() - start_time

        # Determine composite result
        if gate.mode == "all_of":
            all_passed = all(r.passed for r in sub_results)
            if all_passed:
                return GateResult(
                    name=gate.name,
                    status=GateStatus.PASSED,
                    severity=GateSeverity.PASS,
                    output=self._format_sub_results(sub_results),
                    duration_seconds=duration,
                )
            severity = GateSeverity.WARN if gate.warn_only else GateSeverity.FAIL
            status = GateStatus.WARNING if gate.warn_only else GateStatus.FAILED
            return GateResult(
                name=gate.name,
                status=status,
                severity=severity,
                error_output=self._format_sub_results(sub_results),
                duration_seconds=duration,
            )
        else:  # any_of
            any_passed = any(r.passed for r in sub_results)
            if any_passed:
                return GateResult(
                    name=gate.name,
                    status=GateStatus.PASSED,
                    severity=GateSeverity.PASS,
                    output=self._format_sub_results(sub_results),
                    duration_seconds=duration,
                )
            severity = GateSeverity.WARN if gate.warn_only else GateSeverity.FAIL
            status = GateStatus.WARNING if gate.warn_only else GateStatus.FAILED
            return GateResult(
                name=gate.name,
                status=status,
                severity=severity,
                error_output=self._format_sub_results(sub_results),
                duration_seconds=duration,
            )

    @staticmethod
    def _format_sub_results(results: list[GateResult]) -> str:
        """Format sub-gate results into a readable summary."""
        lines = []
        for r in results:
            status_icon = "PASS" if r.passed else "FAIL"
            lines.append(f"  [{status_icon}] {r.name}: {r.status.value}")
        return "\n".join(lines)
