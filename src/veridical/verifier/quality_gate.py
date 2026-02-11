"""Quality gate verification."""

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from veridical.lld.client import LocalLLMClient
from veridical.models.result import GateResult, GateSeverity, GateStatus, VerificationResult
from veridical.verifier.assertion import AssertionGateRunner
from veridical.verifier.composite import CompositeGateRunner
from veridical.verifier.diff_scope import DiffScopeGateRunner
from veridical.verifier.feedback import FeedbackGenerator
from veridical.verifier.runner import CommandRunner
from veridical.verifier.task_completion import verify_task_completion

if TYPE_CHECKING:
    from veridical.config.schema import QualityGate, VeridicalConfig
else:
    from veridical.config.schema import QualityGate

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
        self.assertion_runner = AssertionGateRunner(repo_path)
        self.diff_scope_runner = DiffScopeGateRunner(repo_path)
        self.current_tasks_file: Path | None = None
        self.changed_files: list[str] | None = None
        self.autofix_enabled: bool = True

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

        batches: list[list[QualityGate]] = []
        i = 0
        while i < len(gates):
            gate = gates[i]
            if not gate.parallel:
                # Sequential gates are always in their own batch
                batches.append([gate])
                i += 1
            else:
                # Group consecutive parallel gates into a single batch
                parallel_batch: list[QualityGate] = []
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
        gate_map = dict(zip(tasks, batch, strict=True))
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
                            severity=GateSeverity.FAIL,
                            output=str(e),
                            duration_seconds=0.0,
                        )

        timed_out_tasks: set[asyncio.Task] = set()
        try:
            await asyncio.wait_for(orchestrate(), timeout=self.config.verifier.parallel_timeout)
        except TimeoutError:
            logger.error(
                f"Parallel gate execution timed out after {self.config.verifier.parallel_timeout}s."
            )
            for task in tasks:
                if not task.done():
                    timed_out_tasks.add(task)
                    task.cancel()

        # Ensure all tasks have finished (including cancelled ones) so we don't leak
        # background work into later tests / event loop shutdown.
        await asyncio.gather(*tasks, return_exceptions=True)

        # Collect final results for all tasks
        final_results: dict[str, GateResult] = {}
        for task, gate in zip(tasks, batch, strict=True):
            if gate.name in results:
                final_results[gate.name] = results[gate.name]
                continue

            if task in timed_out_tasks:
                status = GateStatus.TIMEOUT
                output = "Gate execution timed out."
            elif task.cancelled():
                status = GateStatus.CANCELLED
                output = "Cancelled due to failure or timeout in another gate."
            elif task.done() and task.exception():
                status = GateStatus.FAILED
                output = f"An unexpected error occurred: {task.exception()}"
            else:
                status = GateStatus.TIMEOUT
                output = "Gate execution timed out."

            final_results[gate.name] = GateResult(
                name=gate.name, status=status, output=output, duration_seconds=0.0
            )

        return [final_results[g.name] for g in batch]

    def _should_skip_conditional(self, gate: "QualityGate") -> GateResult | None:
        """Check if a gate should be skipped due to when_files_changed condition.

        Returns a SKIPPED GateResult if the gate should be skipped, None otherwise.
        """
        if not gate.when_files_changed:
            return None

        changed = self.changed_files or []
        if not changed:
            logger.info(f"Skipping gate '{gate.name}': no changed files detected")
            return GateResult(
                name=gate.name,
                status=GateStatus.SKIPPED,
                severity=GateSeverity.PASS,
                output=f"Skipped: no changed files matched patterns {gate.when_files_changed}",
                duration_seconds=0.0,
            )

        from veridical.verifier.glob_match import glob_match

        matched = any(
            glob_match(f, pattern) for f in changed for pattern in gate.when_files_changed
        )
        if not matched:
            logger.info(
                f"Skipping gate '{gate.name}': no changed files matched {gate.when_files_changed}"
            )
            return GateResult(
                name=gate.name,
                status=GateStatus.SKIPPED,
                severity=GateSeverity.PASS,
                output=f"Skipped: no changed files matched patterns {gate.when_files_changed}",
                duration_seconds=0.0,
            )

        return None

    async def _run_gate_logic(self, gate: "QualityGate") -> GateResult:
        """Run the logic for a single gate based on its type."""
        logger.info(f"Running quality gate: {gate.name} (type: {gate.type})")

        # Check conditional execution
        skip_result = self._should_skip_conditional(gate)
        if skip_result is not None:
            return skip_result

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
                        severity=GateSeverity.PASS,
                        output="No OpenSpec change detected to verify tasks.",
                        duration_seconds=0.0,
                    )
            else:
                tasks_file_path = self.repo_path / gate.path

            assert tasks_file_path is not None
            return await asyncio.to_thread(verify_task_completion, gate.name, tasks_file_path)
        if gate.type == "assertion":
            return await asyncio.to_thread(self.assertion_runner.run_gate, gate)
        if gate.type == "diff_scope":
            return await asyncio.to_thread(
                self.diff_scope_runner.run_gate, gate, self.changed_files or []
            )
        if gate.type == "composite":
            composite_runner = CompositeGateRunner(self)
            return await composite_runner.run_gate(gate)

        # This should be unreachable due to schema validation
        raise ValueError(f"Unknown quality gate type: {gate.type}")

    def _get_gates_with_task_completion(self) -> list["QualityGate"]:
        """Get quality gates, auto-injecting task_completion if needed.

        If current_tasks_file is set and no task_completion gate exists,
        automatically prepend one to ensure OpenSpec tasks are verified.
        """
        gates = list(self.config.verifier.quality_gates)

        # Check if task_completion gate already exists
        has_task_completion = any(g.type == "task_completion" for g in gates)

        # Auto-inject if we have a tasks file but no task_completion gate
        if self.current_tasks_file and not has_task_completion:
            logger.info("Auto-injecting task_completion gate for OpenSpec verification")
            task_gate = QualityGate(
                name="task_completion",
                type="task_completion",
                path="auto",
                required=True,
            )
            gates.insert(0, task_gate)

        return gates

    async def run_all(self) -> VerificationResult:
        """Run all configured quality gates.

        Returns:
            Aggregated verification result
        """
        start_time = time.monotonic()
        gates = self._get_gates_with_task_completion()
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

        # Autofix phase: attempt fix_command for failed gates that have one
        if self.autofix_enabled:
            fixed_any = False
            for i, result in enumerate(results):
                if result.passed:
                    continue
                # Find the gate config for this result
                gate = next((g for g in gates if g.name == result.name), None)
                if gate is None or not gate.fix_command:
                    continue
                fixed_result = await self._run_autofix(gate)
                if fixed_result is not None:
                    results[i] = fixed_result
                    fixed_any = True
            if fixed_any:
                logger.info("Autofix applied; updated gate results.")

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

    async def _run_autofix(self, gate: "QualityGate") -> GateResult | None:
        """Run a gate's fix_command and re-verify the gate.

        Args:
            gate: The quality gate with a fix_command.

        Returns:
            Updated GateResult if the gate now passes, None otherwise.
        """
        assert gate.fix_command is not None
        logger.info(f"Running autofix for gate '{gate.name}': {gate.fix_command}")

        try:
            fix_process = await asyncio.create_subprocess_shell(
                gate.fix_command,
                cwd=self.repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _stdout, _stderr = await asyncio.wait_for(
                    fix_process.communicate(),
                    timeout=gate.timeout,
                )
            except TimeoutError:
                fix_process.kill()
                await fix_process.wait()
                logger.warning(f"Autofix command for '{gate.name}' timed out after {gate.timeout}s")
                return None

            fix_exit_code = fix_process.returncode or 0
            if fix_exit_code != 0:
                logger.warning(
                    f"Autofix command for '{gate.name}' exited with code {fix_exit_code}"
                )
                return None

        except Exception as e:
            logger.warning(f"Autofix command for '{gate.name}' failed: {e}")
            return None

        # Re-run the gate to see if the fix worked
        logger.info(f"Re-verifying gate '{gate.name}' after autofix")
        re_result = await self._run_gate_logic(gate)
        if re_result.passed:
            logger.info(f"Autofix resolved gate '{gate.name}'")
            return re_result

        logger.info(f"Gate '{gate.name}' still fails after autofix")
        return None

    async def generate_feedback(self, result: VerificationResult) -> str:
        """Generate error feedback from a verification result.

        Args:
            result: Verification result to summarize

        Returns:
            Error context string for the next iteration
        """
        llm_client = None
        if self.config.verifier.local_llm:
            llm_client = LocalLLMClient(self.config.verifier.local_llm)

        try:
            feedback_generator = FeedbackGenerator(
                config=self.config.verifier,
                llm_client=llm_client,
            )
            return await feedback_generator.generate_feedback(result)
        finally:
            if llm_client:
                await llm_client.close()
