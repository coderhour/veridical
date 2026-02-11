"""Test generation gate: diff-aware coverage analysis.

Analyzes the current diff for new/changed functions and cross-references
with coverage data to detect untested code.
"""

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from veridical.config.schema import QualityGate
from veridical.models.result import GateResult, GateSeverity, GateStatus

logger = logging.getLogger(__name__)

# Regex for unified diff hunk headers: @@ -old_start,old_count +new_start,new_count @@
_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

# Regex for Python function/method definitions
_FUNC_DEF_RE = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(")


@dataclass
class DiffFunction:
    """A function definition found in a diff."""

    file_path: str
    line_number: int
    function_name: str


@dataclass
class UncoveredFunction:
    """A function that lacks sufficient test coverage."""

    file_path: str
    line_number: int
    function_name: str
    coverage_percent: float


@dataclass
class CoverageCheckResult:
    """Result of checking coverage for diff functions."""

    uncovered: list[UncoveredFunction] = field(default_factory=list)
    covered_count: int = 0
    total_count: int = 0

    @property
    def all_covered(self) -> bool:
        return len(self.uncovered) == 0


class DiffCoverageAnalyzer:
    """Cross-references git diffs with coverage reports to find untested code."""

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path

    def parse_diff(self, diff_text: str) -> list[DiffFunction]:
        """Extract new/changed function definitions from a unified diff.

        Args:
            diff_text: Unified diff output (e.g. from ``git diff``).

        Returns:
            List of DiffFunction objects for each new/changed function.
        """
        functions: list[DiffFunction] = []
        current_file: str | None = None
        hunk_new_start = 0
        hunk_line_offset = 0

        for line in diff_text.splitlines():
            # Track current file from diff header
            if line.startswith("+++ b/"):
                current_file = line[6:]
                continue

            if line.startswith("--- "):
                continue

            # Track hunk position
            hunk_match = _HUNK_RE.match(line)
            if hunk_match:
                hunk_new_start = int(hunk_match.group(1))
                hunk_line_offset = 0
                continue

            if current_file is None:
                continue

            # Only look at added lines (start with +)
            if line.startswith("+") and not line.startswith("+++"):
                content = line[1:]  # Strip the leading +
                actual_line_number = hunk_new_start + hunk_line_offset

                func_match = _FUNC_DEF_RE.match(content)
                if func_match:
                    functions.append(
                        DiffFunction(
                            file_path=current_file,
                            line_number=actual_line_number,
                            function_name=func_match.group(1),
                        )
                    )
                hunk_line_offset += 1
            elif not line.startswith("-"):
                # Context line (no prefix) — advances position in new file
                hunk_line_offset += 1

        return functions

    def parse_coverage_report(self, report_json: str) -> dict[str, dict[str, list[int]]]:
        """Parse a pytest-cov JSON coverage report.

        Args:
            report_json: JSON string from ``pytest --cov --cov-report=json``.

        Returns:
            Mapping of ``{file_path: {"executed_lines": [...], "missing_lines": [...]}}``.
        """
        data = json.loads(report_json)
        result: dict[str, dict[str, list[int]]] = {}

        files = data.get("files", {})
        for file_path, file_data in files.items():
            result[file_path] = {
                "executed_lines": file_data.get("executed_lines", []),
                "missing_lines": file_data.get("missing_lines", []),
            }

        return result

    def check_coverage(
        self,
        diff_functions: list[DiffFunction],
        coverage_data: dict[str, dict[str, list[int]]],
        threshold: int = 80,
    ) -> CoverageCheckResult:
        """Cross-reference diff functions with coverage data.

        For each function found in the diff, checks whether its definition line
        appears in the executed lines of the coverage report. Functions whose
        definition line is missing from coverage are considered uncovered.

        Args:
            diff_functions: Functions extracted from the diff.
            coverage_data: Parsed coverage report data.
            threshold: Minimum coverage percentage (0-100). Currently used as
                a binary check: a function is "covered" if its definition line
                is executed, "uncovered" otherwise.

        Returns:
            CoverageCheckResult with uncovered functions and counts.
        """
        uncovered: list[UncoveredFunction] = []
        covered_count = 0

        for func in diff_functions:
            file_cov = coverage_data.get(func.file_path)
            if file_cov is None:
                # File not in coverage report at all — uncovered
                coverage_percent = 0.0
                if coverage_percent >= threshold:
                    covered_count += 1
                else:
                    uncovered.append(
                        UncoveredFunction(
                            file_path=func.file_path,
                            line_number=func.line_number,
                            function_name=func.function_name,
                            coverage_percent=coverage_percent,
                        )
                    )
                continue

            executed = set(file_cov.get("executed_lines", []))

            # Check if the function definition line was executed
            coverage_percent = 100.0 if func.line_number in executed else 0.0
            if coverage_percent >= threshold:
                covered_count += 1
            else:
                uncovered.append(
                    UncoveredFunction(
                        file_path=func.file_path,
                        line_number=func.line_number,
                        function_name=func.function_name,
                        coverage_percent=coverage_percent,
                    )
                )

        return CoverageCheckResult(
            uncovered=uncovered,
            covered_count=covered_count,
            total_count=len(diff_functions),
        )

    @staticmethod
    def format_feedback(result: CoverageCheckResult) -> str:
        """Format structured feedback listing uncovered functions.

        Output format per function:
            ``{file}:{line} - {function_name} (coverage: {percent}%)``

        Args:
            result: Coverage check result.

        Returns:
            Human-readable feedback string.
        """
        if result.all_covered:
            return f"All {result.total_count} new/changed functions have test coverage."

        lines = [
            f"Test coverage gap: {len(result.uncovered)} of {result.total_count} "
            f"new/changed functions lack coverage:\n"
        ]
        for func in result.uncovered:
            lines.append(
                f"  {func.file_path}:{func.line_number} - "
                f"{func.function_name} (coverage: {func.coverage_percent:.0f}%)"
            )

        return "\n".join(lines)


class TestCoverageGateRunner:
    """Runs the test_generation quality gate."""

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self.analyzer = DiffCoverageAnalyzer(repo_path)

    async def run_gate(self, gate: QualityGate) -> GateResult:
        """Execute the test_generation gate.

        Steps:
        1. Get the current diff (new/changed code).
        2. Parse diff for new function definitions.
        3. Run the coverage command.
        4. Parse coverage output and cross-reference with diff.
        5. Return pass/fail based on threshold.

        Args:
            gate: Quality gate configuration.

        Returns:
            GateResult indicating pass or fail with structured feedback.
        """
        start_time = time.monotonic()

        # 1. Get current diff
        try:
            diff_text = await self._get_diff()
        except Exception as e:
            return GateResult(
                name=gate.name,
                status=GateStatus.ERROR,
                severity=GateSeverity.FAIL,
                error_output=f"Failed to get diff: {e}",
                duration_seconds=time.monotonic() - start_time,
            )

        # 2. Parse diff for new functions
        diff_functions = self.analyzer.parse_diff(diff_text)

        if not diff_functions:
            return GateResult(
                name=gate.name,
                status=GateStatus.PASSED,
                severity=GateSeverity.PASS,
                output="No new functions detected in diff.",
                duration_seconds=time.monotonic() - start_time,
            )

        # 3. Run coverage command
        coverage_command = gate.coverage_command or "pytest --cov --cov-report=json"
        try:
            coverage_json = await self._run_coverage_command(coverage_command, gate.timeout)
        except Exception as e:
            return GateResult(
                name=gate.name,
                command=coverage_command,
                status=GateStatus.ERROR,
                severity=GateSeverity.FAIL,
                error_output=f"Coverage command failed: {e}",
                duration_seconds=time.monotonic() - start_time,
            )

        # 4. Parse coverage and cross-reference
        try:
            coverage_data = self.analyzer.parse_coverage_report(coverage_json)
        except (json.JSONDecodeError, KeyError) as e:
            return GateResult(
                name=gate.name,
                command=coverage_command,
                status=GateStatus.ERROR,
                severity=GateSeverity.FAIL,
                error_output=f"Failed to parse coverage report: {e}",
                duration_seconds=time.monotonic() - start_time,
            )

        threshold = gate.coverage_threshold or 80
        check_result = self.analyzer.check_coverage(diff_functions, coverage_data, threshold)

        # 5. Build result
        duration = time.monotonic() - start_time
        feedback = DiffCoverageAnalyzer.format_feedback(check_result)

        if check_result.all_covered:
            return GateResult(
                name=gate.name,
                command=coverage_command,
                status=GateStatus.PASSED,
                severity=GateSeverity.PASS,
                output=feedback,
                duration_seconds=duration,
            )

        severity = GateSeverity.WARN if gate.warn_only else GateSeverity.FAIL
        status = GateStatus.WARNING if gate.warn_only else GateStatus.FAILED
        return GateResult(
            name=gate.name,
            command=coverage_command,
            status=status,
            severity=severity,
            error_output=feedback,
            duration_seconds=duration,
        )

    async def _get_diff(self) -> str:
        """Get the current diff against HEAD~1 (or staged if no commits)."""
        process = await asyncio.create_subprocess_exec(
            "git",
            "diff",
            "HEAD~1",
            "--unified=0",
            cwd=self.repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            # Fallback to staged diff
            process = await asyncio.create_subprocess_exec(
                "git",
                "diff",
                "--cached",
                "--unified=0",
                cwd=self.repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                raise RuntimeError(stderr.decode("utf-8", errors="replace"))
        return stdout.decode("utf-8", errors="replace")

    async def _run_coverage_command(self, command: str, timeout: int) -> str:
        """Run the coverage command and return the JSON report contents."""
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=self.repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError as e:
            process.kill()
            await process.wait()
            raise RuntimeError(f"Coverage command timed out after {timeout}s") from e

        # pytest-cov writes to coverage.json by default
        coverage_file = self.repo_path / "coverage.json"
        if coverage_file.exists():
            return coverage_file.read_text()

        # Fallback: try stdout (some configurations output JSON to stdout)
        output = stdout.decode("utf-8", errors="replace")
        try:
            json.loads(output)
            return output
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Coverage command exited with code {process.returncode} "
                f"and no coverage.json found. stderr: {stderr.decode('utf-8', errors='replace')}"
            ) from e
