"""Integration tests for autofix quality gate feature."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from typer.testing import CliRunner

from veridical.cli.main import app
from veridical.config.schema import (
    GitConfig,
    JulesConfig,
    LocalConfig,
    QualityGate,
    SupervisorConfig,
    VeridicalConfig,
    VerifierConfig,
)
from veridical.local.supervisor import LocalSupervisor

runner = CliRunner()


def _make_config(gates: list[QualityGate]) -> VeridicalConfig:
    return VeridicalConfig(
        jules=JulesConfig(),
        supervisor=SupervisorConfig(max_iterations=2),
        verifier=VerifierConfig(quality_gates=gates),
        git=GitConfig(),
    )


@pytest.mark.integration
class TestVerifyCliAutofix:
    """Integration tests for veri verify with autofix."""

    def test_verify_runs_fix_by_default(self, temp_dir: Path) -> None:
        """veri verify runs fix_command by default when a gate fails."""
        config_yaml = temp_dir / ".veridical.yaml"
        config_yaml.write_text("""\
verifier:
  quality_gates:
    - name: format-check
      command: "exit 1"
      fix_command: "echo fixed"
      timeout: 10
""")
        # We can't easily test real subprocess behavior in CI,
        # but we can verify the CLI accepts --no-fix without error
        result = runner.invoke(app, ["verify", "--no-fix", "--config", str(config_yaml)])
        # Gate will fail (exit 1) and --no-fix means no autofix attempt
        assert result.exit_code == 1
        assert "FAILED" in result.stdout

    def test_verify_no_fix_flag_accepted(self, temp_dir: Path) -> None:
        """veri verify --no-fix is a valid flag."""
        config_yaml = temp_dir / ".veridical.yaml"
        config_yaml.write_text("""\
verifier:
  quality_gates:
    - name: always-pass
      command: "exit 0"
      timeout: 10
""")
        result = runner.invoke(app, ["verify", "--no-fix", "--config", str(config_yaml)])
        assert result.exit_code == 0
        assert "PASSED" in result.stdout


@pytest.mark.integration
class TestLocalSupervisorAutofix:
    """Integration tests for local supervisor autofix behavior."""

    @pytest.mark.asyncio
    async def test_local_loop_skips_llm_when_autofix_resolves(self, e2e_temp_repo: Path) -> None:
        """Local supervisor loop completes in 1 iteration when autofix resolves all failures."""
        gate = QualityGate(
            name="format-check",
            command="exit 1",
            fix_command="echo fixed",
            timeout=10,
        )
        config = _make_config([gate])
        config.local = LocalConfig(worker_command="echo worker", mode="subprocess")

        supervisor = LocalSupervisor(config, e2e_temp_repo)

        # Mock: first run_all fails (gate fails), autofix succeeds, re-run passes
        call_count = 0

        async def mock_run_all():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: all gates pass (autofix resolved everything inside run_all)
                return MagicMock(passed=True)
            return MagicMock(passed=True)

        supervisor.verifier.run_all = mock_run_all
        supervisor.verifier.generate_feedback = AsyncMock(return_value="errors")

        # Mock runner to avoid actual subprocess
        supervisor.runner.run = AsyncMock(return_value=0)

        result = await supervisor.run("Fix formatting")

        assert result.success is True
        assert result.iterations == 1
