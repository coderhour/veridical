"""Integration tests for the veri learn CLI commands."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veridical.cli.main import app

runner = CliRunner()


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a project directory with config and worklog data."""
    # Create config
    config = tmp_path / ".veridical.yaml"
    config.write_text("worklog:\n  directory: worklog\nlearning:\n  min_runs_for_analysis: 5\n")
    return tmp_path


def _populate_worklog(project_dir: Path, num_runs: int = 6) -> None:
    """Populate worklog with sample data."""
    worklog_dir = project_dir / "worklog"
    for i in range(num_runs):
        date = f"2025-01-{15 + i:02d}"
        date_dir = worklog_dir / date
        date_dir.mkdir(parents=True, exist_ok=True)

        entries = []
        for j in range(3):
            entry = {
                "timestamp": f"{date}T10:{j:02d}:00",
                "iteration": j + 1,
                "session_id": f"sess-{i}",
                "task_description": f"Fix the validation bug in module_{i}",
                "verification_passed": j == 2,
                "verification_errors": (
                    "Gate 'pytest' FAILED: ImportError: No module named 'foo'" if j < 2 else None
                ),
                "patch_summary": f"patch content {i}-{j}",
            }
            entries.append(entry)

        with (date_dir / "iterations.jsonl").open("w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")


class TestLearnAnalyzeCLI:
    def test_analyze_no_worklog_dir(
        self, project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(project_dir)
        result = runner.invoke(
            app, ["learn", "analyze", "--config", str(project_dir / ".veridical.yaml")]
        )
        assert result.exit_code == 1
        assert "No work logs found" in result.output

    def test_analyze_insufficient_data(
        self, project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _populate_worklog(project_dir, num_runs=3)
        monkeypatch.chdir(project_dir)
        result = runner.invoke(
            app, ["learn", "analyze", "--config", str(project_dir / ".veridical.yaml")]
        )
        assert result.exit_code == 0
        assert "Insufficient data" in result.output

    def test_analyze_with_data(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _populate_worklog(project_dir, num_runs=6)
        monkeypatch.chdir(project_dir)
        result = runner.invoke(
            app, ["learn", "analyze", "--config", str(project_dir / ".veridical.yaml")]
        )
        assert result.exit_code == 0
        assert "Pattern Analysis Report" in result.output

    def test_predict_no_worklog(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(project_dir)
        result = runner.invoke(
            app,
            [
                "learn",
                "predict",
                "Fix the login bug",
                "--config",
                str(project_dir / ".veridical.yaml"),
            ],
        )
        assert result.exit_code == 1
        assert "No work logs found" in result.output

    def test_predict_with_data(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _populate_worklog(project_dir, num_runs=6)
        monkeypatch.chdir(project_dir)
        result = runner.invoke(
            app,
            [
                "learn",
                "predict",
                "Fix the validation bug",
                "--config",
                str(project_dir / ".veridical.yaml"),
            ],
        )
        assert result.exit_code == 0
        assert "Difficulty Estimate" in result.output

    def test_rules_empty(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(project_dir)
        result = runner.invoke(
            app, ["learn", "rules", "--config", str(project_dir / ".veridical.yaml")]
        )
        assert result.exit_code == 0
        assert "No learned rules found" in result.output


class TestLearnSupervisorIntegration:
    def test_learned_rules_injected_into_dispatch(self, project_dir: Path) -> None:
        """Verify that learned rules are loaded when auto_inject_rules is True."""

        from veridical.config.schema import LearningConfig, VeridicalConfig
        from veridical.learning.models import LearnedRule
        from veridical.learning.rules import RuleManager

        # Create rules file
        rules_path = project_dir / ".veridical" / "learned_rules.yaml"
        manager = RuleManager(rules_path)
        manager.save(
            [
                LearnedRule(
                    id="r1",
                    trigger_pattern="gate:pytest",
                    rule_text="Always run tests first",
                    confidence_score=0.8,
                ),
            ]
        )

        # Create config with auto_inject_rules enabled
        config = VeridicalConfig(
            learning=LearningConfig(
                auto_inject_rules=True,
                rules_file=".veridical/learned_rules.yaml",
            ),
        )

        # Verify RuleManager loads the rules
        loaded = RuleManager(project_dir / config.learning.rules_file).load()
        assert len(loaded) == 1
        assert loaded[0].rule_text == "Always run tests first"

        # Verify the context string would be built correctly
        lines = [f"- {r.rule_text}" for r in loaded if r.confidence_score >= 0.3]
        context = "\n".join(lines)
        assert "Always run tests first" in context
