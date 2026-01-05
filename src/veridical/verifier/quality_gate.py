"""Quality gate verification."""

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from veridical.models.result import GateResult, GateStatus, VerificationResult
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
            local_llm_config=config.verifier.local_llm,
        )
        self.current_tasks_file: Path | None = None

    def _group_gates(self, gates: list["QualityGate"]) -> list[list["QualityGate"]]:
        """Group gates into sequential and parallel batches.

        For example, a sequence of gates marked [S, P, P, S, P] will be
        grouped into [[S], [P, P], [S], [P]].

        Args:
            gates: A list of quality gates.

        Returns:
            A list of gate batches.
        """
        if not gates:
            return []

        batches: list[list["QualityGate"]] = []
        i = 0
        while i < len(gates):
            gate = gates[i]
            if not gate.parallel:
                # Sequential gates are always in their own batch
                batches.append([gate])
                i += 1
            else:
                # Group consecutive parallel gates into a single batch
                parallel_batch: list["QualityGate"] = []
                while i < len(gates) and gates[i].parallel:
                    parallel_batch.append(gates[i])
                    i += 1
                batches.append(parallel_batch)
        return batches

    async def _run_parallel_batch(self, batch: list["QualityGate"]) -> list[GateResult]:
        """Run a batch of quality gates in parallel with fail-fast behavior."""
        if not batch:
            return []

        tasks = [asyncio.create_task(self._run_gate_logic(gate)) for gate in batch]
        gate_map = {task: gate for task, gate in zip(tasks, batch)}
        results: dict[str, GateResult] = {}

        async def orchestrate() -> None:
            pending = set(tasks)
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

                for task in done:
                    gate = gate_map[task]
                    try:
                        result = task.result()
                        results[gate.name] = result

                        if not result.passed and gate.required:
                            logger.warning(
                                f"Required gate '{gate.name}' failed; cancelling others."
                            )
                            for p_task in pending:
                                p_task.cancel()
                            return  # Stop processing
                    except asyncio.CancelledError:
                        pass  # Handled in the final collection step
                    except Exception as e:
                        logger.error(f"Error running gate '{gate.name}': {e}", exc_info=True)
                        results[gate.name] = GateResult(
                            name=gate.name,
                            status=GateStatus.FAILED,
                            output=str(e),
                            duration_seconds=0.0,
                        )

        try:
            await asyncio.wait_for(orchestrate(), timeout=self.config.verifier.parallel_timeout)
        except asyncio.TimeoutError:
            logger.error(
                f"Parallel gate execution timed out after {self.config.verifier.parallel_timeout}s."
            )
            for task in tasks:
                if not task.done():
                    task.cancel()

        # Collect final results for all tasks
        final_results: dict[str, GateResult] = {}
        for task, gate in zip(tasks, batch):
            if gate.name in results:
                final_results[gate.name] = results[gate.name]
                continue

            if task.cancelled():
                status = GateStatus.CANCELLED
                output = "Cancelled due to failure or timeout in another gate."
            elif task.done() and task.exception():
                status = GateStatus.FAILED
                output = f"An unexpected error occurred: {task.exception()}"
            else:  # Not in results, not cancelled, no exception -> timed out
                status = GateStatus.TIMEOUT
                output = "Gate execution timed out."

            final_results[gate.name] = GateResult(
                name=gate.name, status=status, output=output, duration_seconds=0.0
            )

        return [final_results[g.name] for g in batch]

    async def _run_gate_logic(self, gate: "QualityGate") -> GateResult:
        """Run the logic for a single gate based on its type."""
        logger.info(f"Running quality gate: {gate.name} (type: {gate.type})")
        if gate.type == "command":
            return await self.runner.run_gate(gate)
        if gate.type == "task_completion":
            # The schema validates that `path` is present for task_completion gates
            assert gate.path is not None

            tasks_file_path: Path | None = None
            if gate.path == "auto":
                if self.current_tasks_file:
                    tasks_file_path = self.current_tasks_file
                else:
                    logger.warning("No dynamic spec detected; skipping task_completion gate")
                    return GateResult(
                        name=gate.name,
                        status=GateStatus.PASSED,
                        output="No OpenSpec change detected to verify tasks.",
                        duration_seconds=0.0,
                    )
            else:
                tasks_file_path = self.repo_path / gate.path

            assert tasks_file_path is not None
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
        gate_batches = self._group_gates(gates)
        results: list[GateResult] = []
        should_stop = False

        for batch in gate_batches:
            if not batch:
                continue

            batch_results: list[GateResult] = []
            if len(batch) > 1:  # Parallel batch
                batch_results = await self._run_parallel_batch(batch)
            else:  # Sequential gate
                result = await self._run_gate_logic(batch[0])
                batch_results.append(result)

            results.extend(batch_results)

            # Check for required failures in the batch and stop if needed
            for result in batch_results:
                gate = next(g for g in batch if g.name == result.name)
                if not result.passed and gate.required:
                    should_stop = True
                    break
            if should_stop:
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
