"""Tests for the autofix quality gate feature."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from veridical.config.schema import (
    GitConfig,
    JulesConfig,
    QualityGate,
    SupervisorConfig,
    VeridicalConfig,
    VerifierConfig,
)
from veridical.models.result import GateResult, GateSeverity, GateStatus
from veridical.verifier.quality_gate import Verifier


def _make_config(gates: list[QualityGate]) -> VeridicalConfig:
    return VeridicalConfig(
        jules=JulesConfig(),
        supervisor=SupervisorConfig(),
        verifier=VerifierConfig(quality_gates=gates),
        git=GitConfig(),
    )


def _failed_result(name: str) -> GateResult:
    return GateResult(
        name=name,
        status=GateStatus.FAILED,
        severity=GateSeverity.FAIL,
        command="check-cmd",
        exit_code=1,
        output="some error",
        error_output="error details",
        duration_seconds=0.1,
    )


def _passed_result(name: str) -> GateResult:
    return GateResult(
        name=name,
        status=GateStatus.PASSED,
        severity=GateSeverity.PASS,
        command="check-cmd",
        exit_code=0,
        output="ok",
        duration_seconds=0.1,
    )


@pytest.mark.unit
class TestAutofixGate:
    """Tests for autofix quality gate behavior."""

    @pytest.mark.asyncio
    async def test_autofix_succeeds(self, tmp_path: Path) -> None:
        """Gate with fix_command passes after autofix runs successfully."""
        gate = QualityGate(
            name="ruff-format",
            command="ruff format --check src/",
            fix_command="ruff format src/",
        )
        config = _make_config([gate])
        verifier = Verifier(config, tmp_path)

        # Mock: gate fails first, fix_command succeeds, re-run passes
        with (
            patch.object(verifier, "_run_gate_logic") as mock_gate_logic,
            patch("asyncio.create_subprocess_shell") as mock_shell,
        ):
            mock_gate_logic.side_effect = [
                _failed_result("ruff-format"),
                _passed_result("ruff-format"),
            ]

            mock_fix_proc = AsyncMock()
            mock_fix_proc.communicate.return_value = (b"", b"")
            mock_fix_proc.returncode = 0
            mock_shell.return_value = mock_fix_proc

            result = await verifier.run_all()

        assert result.passed is True
        assert result.gates[0].status == GateStatus.PASSED

    @pytest.mark.asyncio
    async def test_autofix_still_fails(self, tmp_path: Path) -> None:
        """Gate with fix_command still fails after autofix — original failure reported."""
        gate = QualityGate(
            name="ruff-format",
            command="ruff format --check src/",
            fix_command="ruff format src/",
        )
        config = _make_config([gate])
        verifier = Verifier(config, tmp_path)

        with (
            patch.object(verifier, "_run_gate_logic") as mock_gate_logic,
            patch("asyncio.create_subprocess_shell") as mock_shell,
        ):
            # Gate fails both times
            mock_gate_logic.side_effect = [
                _failed_result("ruff-format"),
                _failed_result("ruff-format"),
            ]

            mock_fix_proc = AsyncMock()
            mock_fix_proc.communicate.return_value = (b"", b"")
            mock_fix_proc.returncode = 0
            mock_shell.return_value = mock_fix_proc

            result = await verifier.run_all()

        assert result.passed is False
        assert result.gates[0].status == GateStatus.FAILED

    @pytest.mark.asyncio
    async def test_fix_command_exits_nonzero(self, tmp_path: Path) -> None:
        """fix_command exits non-zero — warning logged, gate failure unchanged."""
        gate = QualityGate(
            name="ruff-format",
            command="ruff format --check src/",
            fix_command="ruff format src/",
        )
        config = _make_config([gate])
        verifier = Verifier(config, tmp_path)

        with (
            patch.object(verifier, "_run_gate_logic") as mock_gate_logic,
            patch("asyncio.create_subprocess_shell") as mock_shell,
        ):
            mock_gate_logic.return_value = _failed_result("ruff-format")

            mock_fix_proc = AsyncMock()
            mock_fix_proc.communicate.return_value = (b"", b"error")
            mock_fix_proc.returncode = 1
            mock_shell.return_value = mock_fix_proc

            result = await verifier.run_all()

        assert result.passed is False
        # Gate logic should only be called once (no re-run after failed fix)
        mock_gate_logic.assert_called_once()

    @pytest.mark.asyncio
    async def test_autofix_disabled(self, tmp_path: Path) -> None:
        """autofix_enabled=False — fix_command not executed."""
        gate = QualityGate(
            name="ruff-format",
            command="ruff format --check src/",
            fix_command="ruff format src/",
        )
        config = _make_config([gate])
        verifier = Verifier(config, tmp_path)
        verifier.autofix_enabled = False

        with (
            patch.object(verifier, "_run_gate_logic") as mock_gate_logic,
            patch("asyncio.create_subprocess_shell") as mock_shell,
        ):
            mock_gate_logic.return_value = _failed_result("ruff-format")

            result = await verifier.run_all()

        assert result.passed is False
        mock_shell.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_fix_command(self, tmp_path: Path) -> None:
        """Gate without fix_command — no autofix attempt."""
        gate = QualityGate(
            name="pytest",
            command="pytest",
        )
        config = _make_config([gate])
        verifier = Verifier(config, tmp_path)

        with (
            patch.object(verifier, "_run_gate_logic") as mock_gate_logic,
            patch("asyncio.create_subprocess_shell") as mock_shell,
        ):
            mock_gate_logic.return_value = _failed_result("pytest")

            result = await verifier.run_all()

        assert result.passed is False
        mock_shell.assert_not_called()


@pytest.mark.unit
class TestAutofixFixCommandField:
    """Tests for the fix_command field on QualityGate."""

    def test_fix_command_default_none(self) -> None:
        """fix_command defaults to None."""
        gate = QualityGate(name="test", command="echo hi")
        assert gate.fix_command is None

    def test_fix_command_set(self) -> None:
        """fix_command can be set."""
        gate = QualityGate(
            name="ruff-format",
            command="ruff format --check src/",
            fix_command="ruff format src/",
        )
        assert gate.fix_command == "ruff format src/"


@pytest.mark.unit
class TestJulesSupervisorAutofixDisabled:
    """Tests that Jules supervisor disables autofix."""

    def test_jules_supervisor_disables_autofix(self, tmp_path: Path) -> None:
        """Jules Supervisor sets autofix_enabled=False on its verifier."""
        from veridical.supervisor.loop import Supervisor

        config = _make_config([QualityGate(name="pytest", command="pytest")])

        # Supervisor requires a worker; use a minimal mock
        mock_worker = AsyncMock()
        mock_worker.synchronizer = AsyncMock()

        supervisor = Supervisor(config, mock_worker, tmp_path)
        assert supervisor.verifier.autofix_enabled is False


@pytest.mark.unit
class TestLocalSupervisorAutofixEnabled:
    """Tests that LocalSupervisor keeps autofix enabled (default)."""

    def test_local_supervisor_autofix_enabled(self, tmp_path: Path) -> None:
        """LocalSupervisor verifier has autofix_enabled=True by default."""
        from veridical.local.supervisor import LocalSupervisor

        config = _make_config([QualityGate(name="pytest", command="pytest")])
        supervisor = LocalSupervisor(config, tmp_path)
        assert supervisor.verifier.autofix_enabled is True
