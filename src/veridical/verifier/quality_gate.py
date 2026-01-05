"""Quality gate verification."""

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from veridical.models.result import GateResult, VerificationResult
from veridical.verifier.feedback import FeedbackGenerator
from veridical.verifier.runner import CommandRunner
from veridical.verifier.task_completion import verify_task_completion

if TYPE_CHECKING:
    from veridical.config.schema import QualityGate, VeridicalConfig

logger = logging.getLogger(__name__)


class Verifier:
    """Runs quality gates and generates verification results.

    The Verifier is responsible for:
    1. Executing configured quality gates
    2. Collecting and aggregating results
    3. Generating feedback for failed runs
    """

    def __init__(
        self,
        config: "VeridicalConfig",
        repo_path: Path,
    ) -> None:
        """Initialize the verifier.

        Args:
            config: Veridical configuration
            repo_path: Path to the repository root
        """
        self.config = config
        self.repo_path = repo_path
        self.runner = CommandRunner(repo_path)
        self.feedback_generator = FeedbackGenerator(
            max_length=config.verifier.summary_max_length,
        )

    async def _run_gate_logic(self, gate: "QualityGate") -> GateResult:
        """Run the logic for a single gate based on its type."""
        logger.info(f"Running quality gate: {gate.name} (type: {gate.type})")
        if gate.type == "command":
            return await self.runner.run_gate(gate)
        if gate.type == "task_completion":
            if gate.path is None:
                # This should be unreachable due to schema validation
                raise ValueError("`path` is required for 'task_completion' gate type")
            tasks_file_path = self.repo_path / gate.path
            return await asyncio.to_thread(verify_task_completion, gate.name, tasks_file_path)

        # This should be unreachable due to schema validation
        raise ValueError(f"Unknown quality gate type: {gate.type}")

    async def run_all(self) -> VerificationResult:
        """Run all configured quality gates.

        Returns:
            Aggregated verification result
        """
        start_time = time.monotonic()
        gates = self.config.verifier.quality_gates
        results: list[GateResult] = []

        for gate in gates:
            result = await self._run_gate_logic(gate)
            results.append(result)

            # Stop early if a required gate fails
            if not result.passed and gate.required:
                break

        duration = time.monotonic() - start_time
        all_passed = all(r.passed for r in results)

        logger.info(f"Verification completed. Passed: {all_passed}, Duration: {duration:.2f}s")
        return VerificationResult(
            passed=all_passed,
            gates=results,
            duration_seconds=duration,
        )

    async def run_gate(self, gate_name: str) -> VerificationResult:
        """Run a specific quality gate by name.

        Args:
            gate_name: Name of the gate to run

        Returns:
            Verification result for the single gate
        """
        start_time = time.monotonic()

        # Find the gate
        gate = None
        for g in self.config.verifier.quality_gates:
            if g.name == gate_name:
                gate = g
                break

        if gate is None:
            raise ValueError(f"Unknown quality gate: {gate_name}")

        result = await self._run_gate_logic(gate)
        duration = time.monotonic() - start_time

        return VerificationResult(
            passed=result.passed,
            gates=[result],
            duration_seconds=duration,
        )

    def generate_feedback(self, result: VerificationResult) -> str:
        """Generate error feedback from a verification result.

        Args:
            result: Verification result to summarize

        Returns:
            Error context string for the next iteration
        """
        return self.feedback_generator.generate_feedback(result)
