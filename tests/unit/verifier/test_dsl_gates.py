"""Unit tests for verification rule DSL gate types."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from veridical.config.schema import AssertionConfig, QualityGate
from veridical.models.result import GateSeverity, GateStatus
from veridical.verifier.assertion import AssertionGateRunner
from veridical.verifier.composite import CompositeGateRunner
from veridical.verifier.diff_scope import DiffScopeGateRunner
from veridical.verifier.runner import CommandRunner


# ---------------------------------------------------------------------------
# Assertion Gate Tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestAssertionGateRunner:
    """Tests for the AssertionGateRunner."""

    def test_file_exists_pass(self, tmp_path: Path) -> None:
        """Test that assert_file_exists passes when files exist."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")

        gate = QualityGate(
            name="check_files",
            type="assertion",
            assertions=[AssertionConfig(assert_file_exists=["src/main.py"])],
        )
        runner = AssertionGateRunner(tmp_path)
        result = runner.run_gate(gate)

        assert result.passed
        assert result.status == GateStatus.PASSED
        assert result.severity == GateSeverity.PASS

    def test_file_exists_glob_pass(self, tmp_path: Path) -> None:
        """Test that assert_file_exists passes with glob patterns."""
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_foo.py").write_text("")
        (tmp_path / "tests" / "test_bar.py").write_text("")

        gate = QualityGate(
            name="check_tests",
            type="assertion",
            assertions=[AssertionConfig(assert_file_exists=["tests/*.py"])],
        )
        runner = AssertionGateRunner(tmp_path)
        result = runner.run_gate(gate)

        assert result.passed

    def test_file_exists_fail(self, tmp_path: Path) -> None:
        """Test that assert_file_exists fails when files are missing."""
        gate = QualityGate(
            name="check_files",
            type="assertion",
            assertions=[AssertionConfig(assert_file_exists=["nonexistent.py"])],
        )
        runner = AssertionGateRunner(tmp_path)
        result = runner.run_gate(gate)

        assert not result.passed
        assert result.severity == GateSeverity.FAIL
        assert "nonexistent.py" in result.error_output

    def test_content_matches_pass(self, tmp_path: Path) -> None:
        """Test that assert_content_matches passes when pattern matches."""
        readme = tmp_path / "README.md"
        readme.write_text("# My Project\n## Installation\nRun pip install")

        gate = QualityGate(
            name="check_readme",
            type="assertion",
            assertions=[
                AssertionConfig(
                    assert_content_matches={"file": "README.md", "pattern": "## Installation"}
                )
            ],
        )
        runner = AssertionGateRunner(tmp_path)
        result = runner.run_gate(gate)

        assert result.passed

    def test_content_matches_fail(self, tmp_path: Path) -> None:
        """Test that assert_content_matches fails when pattern doesn't match."""
        readme = tmp_path / "README.md"
        readme.write_text("# My Project\nNothing here")

        gate = QualityGate(
            name="check_readme",
            type="assertion",
            assertions=[
                AssertionConfig(
                    assert_content_matches={"file": "README.md", "pattern": "## Installation"}
                )
            ],
        )
        runner = AssertionGateRunner(tmp_path)
        result = runner.run_gate(gate)

        assert not result.passed
        assert "does not match pattern" in result.error_output

    def test_content_matches_file_not_found(self, tmp_path: Path) -> None:
        """Test that assert_content_matches fails when file doesn't exist."""
        gate = QualityGate(
            name="check_missing",
            type="assertion",
            assertions=[
                AssertionConfig(assert_content_matches={"file": "missing.md", "pattern": ".*"})
            ],
        )
        runner = AssertionGateRunner(tmp_path)
        result = runner.run_gate(gate)

        assert not result.passed
        assert "File not found" in result.error_output

    def test_json_schema_pass(self, tmp_path: Path) -> None:
        """Test that assert_json_schema passes with valid JSON."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"name": "test", "version": 1}))

        schema_file = tmp_path / "schema.json"
        schema_file.write_text(
            json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "integer"},
                    },
                    "required": ["name", "version"],
                }
            )
        )

        gate = QualityGate(
            name="check_schema",
            type="assertion",
            assertions=[
                AssertionConfig(assert_json_schema={"file": "config.json", "schema": "schema.json"})
            ],
        )
        runner = AssertionGateRunner(tmp_path)
        result = runner.run_gate(gate)

        # May pass or fail depending on jsonschema availability
        # If jsonschema is not installed, it should fail with a clear message
        if "jsonschema package is required" in (result.error_output or ""):
            pytest.skip("jsonschema not installed")
        assert result.passed

    def test_json_schema_fail(self, tmp_path: Path) -> None:
        """Test that assert_json_schema fails with invalid JSON."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"name": 123}))

        schema_file = tmp_path / "schema.json"
        schema_file.write_text(
            json.dumps(
                {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                }
            )
        )

        gate = QualityGate(
            name="check_schema",
            type="assertion",
            assertions=[
                AssertionConfig(assert_json_schema={"file": "config.json", "schema": "schema.json"})
            ],
        )
        runner = AssertionGateRunner(tmp_path)
        result = runner.run_gate(gate)

        if "jsonschema package is required" in (result.error_output or ""):
            pytest.skip("jsonschema not installed")
        assert not result.passed
        assert "Schema validation failed" in result.error_output

    def test_multiple_assertions(self, tmp_path: Path) -> None:
        """Test gate with multiple assertion configs."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")
        (tmp_path / "README.md").write_text("# Project\n## Installation")

        gate = QualityGate(
            name="multi_check",
            type="assertion",
            assertions=[
                AssertionConfig(assert_file_exists=["src/main.py"]),
                AssertionConfig(
                    assert_content_matches={"file": "README.md", "pattern": "## Installation"}
                ),
            ],
        )
        runner = AssertionGateRunner(tmp_path)
        result = runner.run_gate(gate)

        assert result.passed

    def test_warn_only_assertion(self, tmp_path: Path) -> None:
        """Test that warn_only produces warning severity instead of fail."""
        gate = QualityGate(
            name="check_files",
            type="assertion",
            warn_only=True,
            assertions=[AssertionConfig(assert_file_exists=["nonexistent.py"])],
        )
        runner = AssertionGateRunner(tmp_path)
        result = runner.run_gate(gate)

        assert result.passed  # warn severity means passed
        assert result.severity == GateSeverity.WARN
        assert result.status == GateStatus.WARNING


# ---------------------------------------------------------------------------
# Diff Scope Gate Tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestDiffScopeGateRunner:
    """Tests for the DiffScopeGateRunner."""

    def test_all_files_in_scope(self, tmp_path: Path) -> None:
        """Test that gate passes when all files match allowed patterns."""
        gate = QualityGate(
            name="scope_check",
            type="diff_scope",
            allowed_patterns=["src/**", "tests/**"],
        )
        runner = DiffScopeGateRunner(tmp_path)
        result = runner.run_gate(gate, ["src/main.py", "tests/test_main.py"])

        assert result.passed
        assert result.severity == GateSeverity.PASS

    def test_files_outside_scope(self, tmp_path: Path) -> None:
        """Test that gate fails when files are outside allowed scope."""
        gate = QualityGate(
            name="scope_check",
            type="diff_scope",
            allowed_patterns=["src/**"],
        )
        runner = DiffScopeGateRunner(tmp_path)
        result = runner.run_gate(gate, ["src/main.py", ".github/workflows/ci.yml"])

        assert not result.passed
        assert ".github/workflows/ci.yml" in result.error_output

    def test_no_changes(self, tmp_path: Path) -> None:
        """Test that gate passes when no files were modified."""
        gate = QualityGate(
            name="scope_check",
            type="diff_scope",
            allowed_patterns=["src/**"],
        )
        runner = DiffScopeGateRunner(tmp_path)
        result = runner.run_gate(gate, [])

        assert result.passed

    def test_warn_only_diff_scope(self, tmp_path: Path) -> None:
        """Test that warn_only produces warning severity."""
        gate = QualityGate(
            name="scope_check",
            type="diff_scope",
            warn_only=True,
            allowed_patterns=["src/**"],
        )
        runner = DiffScopeGateRunner(tmp_path)
        result = runner.run_gate(gate, ["dangerous_file.txt"])

        assert result.passed  # warn severity means passed
        assert result.severity == GateSeverity.WARN


# ---------------------------------------------------------------------------
# Conditional Gate Tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestConditionalGate:
    """Tests for the when_files_changed conditional gate modifier."""

    @pytest.fixture
    def verifier(self):
        config = MagicMock()
        config.verifier.parallel_timeout = 10
        config.verifier.quality_gates = []
        from veridical.verifier.quality_gate import Verifier

        v = Verifier(config=config, repo_path=Path("/tmp"))
        return v

    @pytest.mark.asyncio
    async def test_gate_runs_when_files_match(self, verifier) -> None:
        """Test that gate runs when changed files match the pattern."""
        verifier.changed_files = ["src/main.py", "src/utils.py"]

        gate = QualityGate(
            name="pytest",
            type="command",
            command="echo ok",
            when_files_changed=["src/**/*.py"],
        )

        result = verifier._should_skip_conditional(gate)
        assert result is None  # Not skipped

    @pytest.mark.asyncio
    async def test_gate_skipped_when_no_files_match(self, verifier) -> None:
        """Test that gate is skipped when no changed files match."""
        verifier.changed_files = ["docs/README.md"]

        gate = QualityGate(
            name="pytest",
            type="command",
            command="echo ok",
            when_files_changed=["src/**/*.py"],
        )

        result = verifier._should_skip_conditional(gate)
        assert result is not None
        assert result.status == GateStatus.SKIPPED
        assert result.severity == GateSeverity.PASS

    @pytest.mark.asyncio
    async def test_gate_skipped_when_no_changed_files(self, verifier) -> None:
        """Test that gate is skipped when changed_files is empty."""
        verifier.changed_files = []

        gate = QualityGate(
            name="pytest",
            type="command",
            command="echo ok",
            when_files_changed=["src/**/*.py"],
        )

        result = verifier._should_skip_conditional(gate)
        assert result is not None
        assert result.status == GateStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_gate_not_conditional(self, verifier) -> None:
        """Test that gate without when_files_changed is not skipped."""
        verifier.changed_files = ["docs/README.md"]

        gate = QualityGate(
            name="pytest",
            type="command",
            command="echo ok",
        )

        result = verifier._should_skip_conditional(gate)
        assert result is None  # Not skipped


# ---------------------------------------------------------------------------
# Composite Gate Tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestCompositeGateRunner:
    """Tests for the CompositeGateRunner."""

    @pytest.fixture
    def mock_verifier(self):
        verifier = MagicMock()
        return verifier

    @pytest.mark.asyncio
    async def test_all_of_pass(self, mock_verifier) -> None:
        """Test all_of composite passes when all sub-gates pass."""
        from veridical.models.result import GateResult

        async def mock_run_gate_logic(gate):
            return GateResult(
                name=gate.name,
                status=GateStatus.PASSED,
                severity=GateSeverity.PASS,
                duration_seconds=0.1,
            )

        mock_verifier._run_gate_logic = AsyncMock(side_effect=mock_run_gate_logic)

        gate = QualityGate(
            name="all_checks",
            type="composite",
            mode="all_of",
            gates=[
                QualityGate(name="sub1", type="command", command="echo 1"),
                QualityGate(name="sub2", type="command", command="echo 2"),
            ],
        )

        runner = CompositeGateRunner(mock_verifier)
        result = await runner.run_gate(gate)

        assert result.passed
        assert result.severity == GateSeverity.PASS

    @pytest.mark.asyncio
    async def test_all_of_fail(self, mock_verifier) -> None:
        """Test all_of composite fails when any sub-gate fails."""
        from veridical.models.result import GateResult

        call_count = 0

        async def mock_run_gate_logic(gate):
            nonlocal call_count
            call_count += 1
            if gate.name == "sub1":
                return GateResult(
                    name=gate.name,
                    status=GateStatus.PASSED,
                    severity=GateSeverity.PASS,
                    duration_seconds=0.1,
                )
            return GateResult(
                name=gate.name,
                status=GateStatus.FAILED,
                severity=GateSeverity.FAIL,
                duration_seconds=0.1,
            )

        mock_verifier._run_gate_logic = AsyncMock(side_effect=mock_run_gate_logic)

        gate = QualityGate(
            name="all_checks",
            type="composite",
            mode="all_of",
            gates=[
                QualityGate(name="sub1", type="command", command="echo 1"),
                QualityGate(name="sub2", type="command", command="echo 2"),
                QualityGate(name="sub3", type="command", command="echo 3"),
            ],
        )

        runner = CompositeGateRunner(mock_verifier)
        result = await runner.run_gate(gate)

        assert not result.passed
        assert result.severity == GateSeverity.FAIL
        # Early exit: sub3 should not run
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_any_of_pass(self, mock_verifier) -> None:
        """Test any_of composite passes when at least one sub-gate passes."""
        from veridical.models.result import GateResult

        call_count = 0

        async def mock_run_gate_logic(gate):
            nonlocal call_count
            call_count += 1
            if gate.name == "sub1":
                return GateResult(
                    name=gate.name,
                    status=GateStatus.FAILED,
                    severity=GateSeverity.FAIL,
                    duration_seconds=0.1,
                )
            return GateResult(
                name=gate.name,
                status=GateStatus.PASSED,
                severity=GateSeverity.PASS,
                duration_seconds=0.1,
            )

        mock_verifier._run_gate_logic = AsyncMock(side_effect=mock_run_gate_logic)

        gate = QualityGate(
            name="any_check",
            type="composite",
            mode="any_of",
            gates=[
                QualityGate(name="sub1", type="command", command="echo 1"),
                QualityGate(name="sub2", type="command", command="echo 2"),
                QualityGate(name="sub3", type="command", command="echo 3"),
            ],
        )

        runner = CompositeGateRunner(mock_verifier)
        result = await runner.run_gate(gate)

        assert result.passed
        # Early exit: sub3 should not run since sub2 passed
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_any_of_fail(self, mock_verifier) -> None:
        """Test any_of composite fails when all sub-gates fail."""
        from veridical.models.result import GateResult

        async def mock_run_gate_logic(gate):
            return GateResult(
                name=gate.name,
                status=GateStatus.FAILED,
                severity=GateSeverity.FAIL,
                duration_seconds=0.1,
            )

        mock_verifier._run_gate_logic = AsyncMock(side_effect=mock_run_gate_logic)

        gate = QualityGate(
            name="any_check",
            type="composite",
            mode="any_of",
            gates=[
                QualityGate(name="sub1", type="command", command="echo 1"),
                QualityGate(name="sub2", type="command", command="echo 2"),
            ],
        )

        runner = CompositeGateRunner(mock_verifier)
        result = await runner.run_gate(gate)

        assert not result.passed
        assert result.severity == GateSeverity.FAIL

    @pytest.mark.asyncio
    async def test_nested_composite(self, mock_verifier) -> None:
        """Test nested composite gates (composite containing composites)."""
        from veridical.models.result import GateResult

        async def mock_run_gate_logic(gate):
            if gate.type == "composite":
                runner = CompositeGateRunner(mock_verifier)
                return await runner.run_gate(gate)
            return GateResult(
                name=gate.name,
                status=GateStatus.PASSED,
                severity=GateSeverity.PASS,
                duration_seconds=0.1,
            )

        mock_verifier._run_gate_logic = AsyncMock(side_effect=mock_run_gate_logic)

        inner_composite = QualityGate(
            name="inner",
            type="composite",
            mode="all_of",
            gates=[
                QualityGate(name="inner_sub1", type="command", command="echo 1"),
                QualityGate(name="inner_sub2", type="command", command="echo 2"),
            ],
        )

        gate = QualityGate(
            name="outer",
            type="composite",
            mode="all_of",
            gates=[
                inner_composite,
                QualityGate(name="outer_sub1", type="command", command="echo 3"),
            ],
        )

        runner = CompositeGateRunner(mock_verifier)
        result = await runner.run_gate(gate)

        assert result.passed

    @pytest.mark.asyncio
    async def test_composite_warn_only(self, mock_verifier) -> None:
        """Test that warn_only on composite produces warning severity."""
        from veridical.models.result import GateResult

        async def mock_run_gate_logic(gate):
            return GateResult(
                name=gate.name,
                status=GateStatus.FAILED,
                severity=GateSeverity.FAIL,
                duration_seconds=0.1,
            )

        mock_verifier._run_gate_logic = AsyncMock(side_effect=mock_run_gate_logic)

        gate = QualityGate(
            name="warn_composite",
            type="composite",
            mode="all_of",
            warn_only=True,
            gates=[
                QualityGate(name="sub1", type="command", command="echo 1"),
            ],
        )

        runner = CompositeGateRunner(mock_verifier)
        result = await runner.run_gate(gate)

        assert result.passed  # warn severity means passed
        assert result.severity == GateSeverity.WARN


# ---------------------------------------------------------------------------
# Warning and Exit Code Tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestWarnOnlyAndExitCodeMap:
    """Tests for warn_only and exit_code_map features."""

    def test_resolve_exit_code_default_pass(self) -> None:
        """Test default exit code 0 resolves to pass."""
        status, severity = CommandRunner._resolve_exit_code(0, None, False)
        assert status == GateStatus.PASSED
        assert severity == GateSeverity.PASS

    def test_resolve_exit_code_default_fail(self) -> None:
        """Test default non-zero exit code resolves to fail."""
        status, severity = CommandRunner._resolve_exit_code(1, None, False)
        assert status == GateStatus.FAILED
        assert severity == GateSeverity.FAIL

    def test_resolve_exit_code_warn_only(self) -> None:
        """Test warn_only converts failure to warning."""
        status, severity = CommandRunner._resolve_exit_code(1, None, True)
        assert status == GateStatus.WARNING
        assert severity == GateSeverity.WARN

    def test_resolve_exit_code_warn_only_pass(self) -> None:
        """Test warn_only doesn't affect passing exit code."""
        status, severity = CommandRunner._resolve_exit_code(0, None, True)
        assert status == GateStatus.PASSED
        assert severity == GateSeverity.PASS

    def test_exit_code_map_pass(self) -> None:
        """Test exit_code_map mapping to pass."""
        status, severity = CommandRunner._resolve_exit_code(0, {0: "pass"}, False)
        assert status == GateStatus.PASSED
        assert severity == GateSeverity.PASS

    def test_exit_code_map_warn(self) -> None:
        """Test exit_code_map mapping to warn."""
        status, severity = CommandRunner._resolve_exit_code(2, {2: "warn"}, False)
        assert status == GateStatus.WARNING
        assert severity == GateSeverity.WARN

    def test_exit_code_map_fail(self) -> None:
        """Test exit_code_map mapping to fail."""
        status, severity = CommandRunner._resolve_exit_code(1, {1: "fail"}, False)
        assert status == GateStatus.FAILED
        assert severity == GateSeverity.FAIL

    def test_exit_code_map_unmapped_code(self) -> None:
        """Test exit_code_map falls back to default for unmapped codes."""
        status, severity = CommandRunner._resolve_exit_code(3, {1: "fail", 2: "warn"}, False)
        assert status == GateStatus.FAILED
        assert severity == GateSeverity.FAIL

    def test_exit_code_map_overrides_warn_only(self) -> None:
        """Test that exit_code_map takes precedence over warn_only."""
        status, severity = CommandRunner._resolve_exit_code(1, {1: "fail"}, True)
        assert status == GateStatus.FAILED
        assert severity == GateSeverity.FAIL


# ---------------------------------------------------------------------------
# Config Validation Tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestQualityGateValidation:
    """Tests for QualityGate config validation."""

    def test_assertion_gate_requires_assertions(self) -> None:
        """Test that assertion gate type requires assertions field."""
        with pytest.raises(ValueError, match="`assertions` is required"):
            QualityGate(name="test", type="assertion")

    def test_diff_scope_gate_requires_allowed_patterns(self) -> None:
        """Test that diff_scope gate type requires allowed_patterns field."""
        with pytest.raises(ValueError, match="`allowed_patterns` is required"):
            QualityGate(name="test", type="diff_scope")

    def test_composite_gate_requires_mode(self) -> None:
        """Test that composite gate type requires mode field."""
        with pytest.raises(ValueError, match="`mode` is required"):
            QualityGate(
                name="test",
                type="composite",
                gates=[QualityGate(name="sub", type="command", command="echo")],
            )

    def test_composite_gate_requires_gates(self) -> None:
        """Test that composite gate type requires gates field."""
        with pytest.raises(ValueError, match="`gates` is required"):
            QualityGate(name="test", type="composite", mode="all_of")

    def test_exit_code_map_invalid_outcome(self) -> None:
        """Test that invalid exit_code_map outcomes are rejected."""
        with pytest.raises(ValueError, match="Invalid exit_code_map outcome"):
            QualityGate(
                name="test",
                type="command",
                command="echo",
                exit_code_map={0: "invalid"},
            )

    def test_valid_exit_code_map(self) -> None:
        """Test that valid exit_code_map is accepted."""
        gate = QualityGate(
            name="test",
            type="command",
            command="echo",
            exit_code_map={0: "pass", 1: "fail", 2: "warn"},
        )
        assert gate.exit_code_map == {0: "pass", 1: "fail", 2: "warn"}

    def test_warn_only_field(self) -> None:
        """Test that warn_only field is accepted."""
        gate = QualityGate(name="test", type="command", command="echo", warn_only=True)
        assert gate.warn_only is True

    def test_when_files_changed_field(self) -> None:
        """Test that when_files_changed field is accepted."""
        gate = QualityGate(
            name="test",
            type="command",
            command="echo",
            when_files_changed=["src/**/*.py"],
        )
        assert gate.when_files_changed == ["src/**/*.py"]

    def test_backward_compatible_command_gate(self) -> None:
        """Test that existing command gates still work."""
        gate = QualityGate(name="pytest", command="pytest")
        assert gate.type == "command"
        assert gate.warn_only is False
        assert gate.when_files_changed is None
        assert gate.exit_code_map is None
