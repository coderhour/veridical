"""Integration tests for the test_generation quality gate."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from veridical.config.schema import QualityGate
from veridical.models.result import GateStatus
from veridical.verifier.test_coverage import TestCoverageGateRunner as CoverageGateRunner


def _make_gate(**kwargs) -> QualityGate:
    defaults = {
        "name": "test_coverage",
        "type": "test_generation",
        "coverage_command": "pytest --cov --cov-report=json",
        "coverage_threshold": 80,
    }
    defaults.update(kwargs)
    return QualityGate(**defaults)


DIFF_WITH_UNCOVERED = """\
diff --git a/src/auth.py b/src/auth.py
new file mode 100644
--- /dev/null
+++ b/src/auth.py
@@ -0,0 +1,10 @@
+def validate_password(password: str) -> bool:
+    return len(password) >= 8
+
+
+def hash_password(password: str) -> str:
+    return "hashed"
"""

COVERAGE_PARTIAL = {
    "files": {
        "src/auth.py": {
            "executed_lines": [1, 2],
            "missing_lines": [5, 6],
        }
    }
}

COVERAGE_FULL = {
    "files": {
        "src/auth.py": {
            "executed_lines": [1, 2, 5, 6],
            "missing_lines": [],
        }
    }
}

DIFF_NO_FUNCTIONS = """\
diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1,2 +1,3 @@
 # Project
+Added a line
 Old content
"""


@pytest.mark.integration
class TestTestGenerationGateFails:
    """Integration test: gate fails when new function lacks coverage (task 4.3)."""

    @pytest.mark.asyncio
    async def test_gate_fails_uncovered_function(self, tmp_path: Path) -> None:
        """Gate should fail when diff introduces a function not covered by tests."""
        runner = CoverageGateRunner(tmp_path)
        gate = _make_gate()

        with (
            patch.object(
                runner, "_get_diff", new_callable=AsyncMock, return_value=DIFF_WITH_UNCOVERED
            ),
            patch.object(
                runner,
                "_run_coverage_command",
                new_callable=AsyncMock,
                return_value=json.dumps(COVERAGE_PARTIAL),
            ),
        ):
            result = await runner.run_gate(gate)

        assert result.status == GateStatus.FAILED
        assert "hash_password" in result.error_output

    @pytest.mark.asyncio
    async def test_gate_fails_with_threshold_message(self, tmp_path: Path) -> None:
        """Failure output should mention the coverage shortfall."""
        runner = CoverageGateRunner(tmp_path)
        gate = _make_gate(coverage_threshold=80)

        with (
            patch.object(
                runner, "_get_diff", new_callable=AsyncMock, return_value=DIFF_WITH_UNCOVERED
            ),
            patch.object(
                runner,
                "_run_coverage_command",
                new_callable=AsyncMock,
                return_value=json.dumps(COVERAGE_PARTIAL),
            ),
        ):
            result = await runner.run_gate(gate)

        assert result.status == GateStatus.FAILED
        assert "lack coverage" in result.error_output


@pytest.mark.integration
class TestTestGenerationGatePasses:
    """Integration test: gate passes when all new functions are covered (task 4.4)."""

    @pytest.mark.asyncio
    async def test_gate_passes_all_covered(self, tmp_path: Path) -> None:
        """Gate should pass when all new functions have coverage."""
        runner = CoverageGateRunner(tmp_path)
        gate = _make_gate()

        with (
            patch.object(
                runner, "_get_diff", new_callable=AsyncMock, return_value=DIFF_WITH_UNCOVERED
            ),
            patch.object(
                runner,
                "_run_coverage_command",
                new_callable=AsyncMock,
                return_value=json.dumps(COVERAGE_FULL),
            ),
        ):
            result = await runner.run_gate(gate)

        assert result.status == GateStatus.PASSED
        assert "All" in result.output

    @pytest.mark.asyncio
    async def test_gate_passes_no_new_functions(self, tmp_path: Path) -> None:
        """Gate should pass when diff has no new functions."""
        runner = CoverageGateRunner(tmp_path)
        gate = _make_gate()

        with patch.object(
            runner, "_get_diff", new_callable=AsyncMock, return_value=DIFF_NO_FUNCTIONS
        ):
            result = await runner.run_gate(gate)

        assert result.status == GateStatus.PASSED
        assert "No new functions" in result.output


@pytest.mark.integration
class TestStructuredFeedback:
    """Integration test: structured feedback contains correct file:line references (task 4.5)."""

    @pytest.mark.asyncio
    async def test_feedback_contains_file_line_references(self, tmp_path: Path) -> None:
        """Feedback should list uncovered functions with file:line format."""
        runner = CoverageGateRunner(tmp_path)
        gate = _make_gate()

        with (
            patch.object(
                runner, "_get_diff", new_callable=AsyncMock, return_value=DIFF_WITH_UNCOVERED
            ),
            patch.object(
                runner,
                "_run_coverage_command",
                new_callable=AsyncMock,
                return_value=json.dumps(COVERAGE_PARTIAL),
            ),
        ):
            result = await runner.run_gate(gate)

        assert "src/auth.py:5" in result.error_output
        assert "hash_password" in result.error_output
        assert "coverage: 0%" in result.error_output

    @pytest.mark.asyncio
    async def test_feedback_lists_all_uncovered(self, tmp_path: Path) -> None:
        """Feedback should list every uncovered function."""
        # Coverage report with nothing executed
        empty_coverage = {
            "files": {"src/auth.py": {"executed_lines": [], "missing_lines": [1, 2, 5, 6]}}
        }
        runner = CoverageGateRunner(tmp_path)
        gate = _make_gate()

        with (
            patch.object(
                runner, "_get_diff", new_callable=AsyncMock, return_value=DIFF_WITH_UNCOVERED
            ),
            patch.object(
                runner,
                "_run_coverage_command",
                new_callable=AsyncMock,
                return_value=json.dumps(empty_coverage),
            ),
        ):
            result = await runner.run_gate(gate)

        assert "validate_password" in result.error_output
        assert "hash_password" in result.error_output
        assert "2 of 2" in result.error_output
