"""Unit tests for DiffCoverageAnalyzer and TestCoverageGateRunner."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from veridical.config.schema import QualityGate
from veridical.verifier.test_coverage import (
    CoverageCheckResult,
    DiffCoverageAnalyzer,
    DiffFunction,
    UncoveredFunction,
)

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_DIFF = """\
diff --git a/src/auth.py b/src/auth.py
new file mode 100644
--- /dev/null
+++ b/src/auth.py
@@ -0,0 +1,20 @@
+import hashlib
+
+
+def validate_password(password: str) -> bool:
+    return len(password) >= 8
+
+
+def hash_password(password: str) -> str:
+    return hashlib.sha256(password.encode()).hexdigest()
+
+
+class AuthService:
+    def login(self, username: str, password: str) -> bool:
+        return True
+
+
+async def refresh_token(token: str) -> str:
+    return token
"""

SAMPLE_DIFF_MODIFY = """\
diff --git a/src/utils.py b/src/utils.py
--- a/src/utils.py
+++ b/src/utils.py
@@ -10,3 +10,8 @@ def existing_func():
     return True


+def new_helper(x: int) -> int:
+    return x * 2
+
+
+def another_helper(y: str) -> str:
+    return y.strip()
"""

SAMPLE_COVERAGE_REPORT = {
    "files": {
        "src/auth.py": {
            "executed_lines": [1, 4, 5, 8, 9, 12, 13, 14],
            "missing_lines": [17, 18],
        },
        "src/utils.py": {
            "executed_lines": [10, 11, 13, 14],
            "missing_lines": [17, 18],
        },
    }
}


@pytest.mark.unit
class TestDiffParsing:
    """Tests for DiffCoverageAnalyzer.parse_diff (task 1.2)."""

    def setup_method(self) -> None:
        self.analyzer = DiffCoverageAnalyzer(Path("/tmp/repo"))

    def test_parse_new_file_functions(self) -> None:
        """Extract function definitions from a new file diff."""
        functions = self.analyzer.parse_diff(SAMPLE_DIFF)
        names = [f.function_name for f in functions]

        assert "validate_password" in names
        assert "hash_password" in names
        assert "login" in names
        assert "refresh_token" in names
        assert len(functions) == 4

    def test_parse_function_file_paths(self) -> None:
        """All functions should reference the correct file."""
        functions = self.analyzer.parse_diff(SAMPLE_DIFF)
        assert all(f.file_path == "src/auth.py" for f in functions)

    def test_parse_function_line_numbers(self) -> None:
        """Line numbers should match the new-file side of the diff."""
        functions = self.analyzer.parse_diff(SAMPLE_DIFF)
        by_name = {f.function_name: f for f in functions}

        assert by_name["validate_password"].line_number == 4
        assert by_name["hash_password"].line_number == 8
        assert by_name["login"].line_number == 13
        assert by_name["refresh_token"].line_number == 17

    def test_parse_modified_file(self) -> None:
        """Extract functions from a modification diff."""
        functions = self.analyzer.parse_diff(SAMPLE_DIFF_MODIFY)
        names = [f.function_name for f in functions]

        assert "new_helper" in names
        assert "another_helper" in names
        assert len(functions) == 2

    def test_parse_modified_file_line_numbers(self) -> None:
        """Line numbers for modified file should be correct."""
        functions = self.analyzer.parse_diff(SAMPLE_DIFF_MODIFY)
        by_name = {f.function_name: f for f in functions}

        assert by_name["new_helper"].line_number == 13
        assert by_name["another_helper"].line_number == 17

    def test_parse_empty_diff(self) -> None:
        """Empty diff should return no functions."""
        assert self.analyzer.parse_diff("") == []

    def test_parse_diff_no_functions(self) -> None:
        """Diff with no function definitions should return empty list."""
        diff = """\
diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1,2 +1,3 @@
 # Project
+New line added
 Old line
"""
        assert self.analyzer.parse_diff(diff) == []

    def test_parse_async_function(self) -> None:
        """Async function definitions should be detected."""
        functions = self.analyzer.parse_diff(SAMPLE_DIFF)
        async_funcs = [f for f in functions if f.function_name == "refresh_token"]
        assert len(async_funcs) == 1


@pytest.mark.unit
class TestCoverageReportParsing:
    """Tests for DiffCoverageAnalyzer.parse_coverage_report (task 1.3)."""

    def setup_method(self) -> None:
        self.analyzer = DiffCoverageAnalyzer(Path("/tmp/repo"))

    def test_parse_valid_report(self) -> None:
        """Parse a valid pytest-cov JSON report."""
        report_json = json.dumps(SAMPLE_COVERAGE_REPORT)
        result = self.analyzer.parse_coverage_report(report_json)

        assert "src/auth.py" in result
        assert "src/utils.py" in result
        assert 4 in result["src/auth.py"]["executed_lines"]
        assert 17 in result["src/auth.py"]["missing_lines"]

    def test_parse_empty_report(self) -> None:
        """Empty files dict should return empty result."""
        result = self.analyzer.parse_coverage_report('{"files": {}}')
        assert result == {}

    def test_parse_invalid_json(self) -> None:
        """Invalid JSON should raise."""
        with pytest.raises(json.JSONDecodeError):
            self.analyzer.parse_coverage_report("not json")


@pytest.mark.unit
class TestCoverageCheck:
    """Tests for DiffCoverageAnalyzer.check_coverage (task 1.4)."""

    def setup_method(self) -> None:
        self.analyzer = DiffCoverageAnalyzer(Path("/tmp/repo"))

    def test_all_covered(self) -> None:
        """Functions whose definition lines are executed should be covered."""
        diff_functions = [
            DiffFunction(file_path="src/auth.py", line_number=4, function_name="validate_password"),
            DiffFunction(file_path="src/auth.py", line_number=8, function_name="hash_password"),
        ]
        coverage_data = {
            "src/auth.py": {
                "executed_lines": [4, 5, 8, 9],
                "missing_lines": [],
            }
        }
        result = self.analyzer.check_coverage(diff_functions, coverage_data)
        assert result.all_covered
        assert result.covered_count == 2
        assert result.total_count == 2

    def test_uncovered_function(self) -> None:
        """Functions whose definition lines are missing should be uncovered."""
        diff_functions = [
            DiffFunction(file_path="src/auth.py", line_number=4, function_name="validate_password"),
            DiffFunction(file_path="src/auth.py", line_number=17, function_name="refresh_token"),
        ]
        coverage_data = {
            "src/auth.py": {
                "executed_lines": [4, 5],
                "missing_lines": [17, 18],
            }
        }
        result = self.analyzer.check_coverage(diff_functions, coverage_data)
        assert not result.all_covered
        assert result.covered_count == 1
        assert len(result.uncovered) == 1
        assert result.uncovered[0].function_name == "refresh_token"

    def test_file_not_in_coverage(self) -> None:
        """Functions in files not present in coverage report should be uncovered."""
        diff_functions = [
            DiffFunction(file_path="src/new_module.py", line_number=1, function_name="new_func"),
        ]
        result = self.analyzer.check_coverage(diff_functions, {})
        assert not result.all_covered
        assert result.uncovered[0].coverage_percent == 0.0

    def test_empty_diff_functions(self) -> None:
        """No diff functions should result in all covered."""
        result = self.analyzer.check_coverage([], {})
        assert result.all_covered
        assert result.total_count == 0


@pytest.mark.unit
class TestFeedbackFormatting:
    """Tests for DiffCoverageAnalyzer.format_feedback (task 1.5)."""

    def test_all_covered_feedback(self) -> None:
        """Feedback for all-covered result."""
        result = CoverageCheckResult(uncovered=[], covered_count=3, total_count=3)
        feedback = DiffCoverageAnalyzer.format_feedback(result)
        assert "All 3" in feedback
        assert "coverage" in feedback.lower()

    def test_uncovered_feedback_format(self) -> None:
        """Feedback should list uncovered functions with file:line references."""
        result = CoverageCheckResult(
            uncovered=[
                UncoveredFunction(
                    file_path="src/auth.py",
                    line_number=42,
                    function_name="validate_password",
                    coverage_percent=0.0,
                ),
                UncoveredFunction(
                    file_path="src/utils.py",
                    line_number=10,
                    function_name="helper",
                    coverage_percent=0.0,
                ),
            ],
            covered_count=1,
            total_count=3,
        )
        feedback = DiffCoverageAnalyzer.format_feedback(result)

        assert "src/auth.py:42 - validate_password (coverage: 0%)" in feedback
        assert "src/utils.py:10 - helper (coverage: 0%)" in feedback
        assert "2 of 3" in feedback


@pytest.mark.unit
class TestSchemaAcceptsTestGeneration:
    """Tests for QualityGate schema accepting test_generation type (task 4.2)."""

    def test_test_generation_type_accepted(self) -> None:
        """Schema should accept test_generation type."""
        gate = QualityGate(name="coverage", type="test_generation")
        assert gate.type == "test_generation"

    def test_test_generation_with_all_fields(self) -> None:
        """Schema should accept all coverage-specific fields."""
        gate = QualityGate(
            name="coverage",
            type="test_generation",
            coverage_command="pytest --cov --cov-report=json",
            coverage_threshold=90,
            coverage_format="pytest-cov-json",
        )
        assert gate.coverage_command == "pytest --cov --cov-report=json"
        assert gate.coverage_threshold == 90
        assert gate.coverage_format == "pytest-cov-json"

    def test_test_generation_defaults(self) -> None:
        """Coverage fields should default to None (runtime defaults applied later)."""
        gate = QualityGate(name="coverage", type="test_generation")
        assert gate.coverage_command is None
        assert gate.coverage_threshold is None
        assert gate.coverage_format is None

    def test_coverage_threshold_bounds(self) -> None:
        """Threshold must be 0-100."""
        with pytest.raises(ValidationError):
            QualityGate(name="coverage", type="test_generation", coverage_threshold=101)
        with pytest.raises(ValidationError):
            QualityGate(name="coverage", type="test_generation", coverage_threshold=-1)
