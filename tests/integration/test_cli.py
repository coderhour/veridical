"""Integration tests for the CLI."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from veridical.cli.main import app
from veridical.config.defaults import TemplateType

runner = CliRunner()


@pytest.mark.integration
class TestCliConfigCommands:
    """Integration tests for the 'config' CLI commands."""

    def test_config_init_default(self, temp_dir: Path) -> None:
        """Test 'config init' with default settings."""
        result = runner.invoke(app, ["config", "init", "--output", str(temp_dir / "config.yaml")])
        assert result.exit_code == 0
        assert "Created configuration file" in result.stdout
        assert "Python" in (temp_dir / "config.yaml").read_text()

    @pytest.mark.parametrize(
        "template_type, expected_title",
        [
            (TemplateType.PYTHON, "(Python)"),
            (TemplateType.NODEJS, "(Node.js)"),
            (TemplateType.ELIXIR, "(Elixir)"),
            (TemplateType.JAVA, "(Java with Gradle)"),
            (TemplateType.GO, "(Go)"),
            (TemplateType.RUST, "(Rust)"),
            (TemplateType.TYPESCRIPT, "(TypeScript)"),
            (TemplateType.RUBY, "(Ruby)"),
            (TemplateType.PHP, "(PHP)"),
            (TemplateType.DOTNET, "(C#/.NET)"),
        ],
    )
    def test_config_init_templates(
        self,
        temp_dir: Path,
        template_type: TemplateType,
        expected_title: str,
    ) -> None:
        """Test 'config init' with different templates."""
        output_file = temp_dir / f"config.{template_type.value}.yaml"
        result = runner.invoke(
            app,
            [
                "config",
                "init",
                "--output",
                str(output_file),
                "--template",
                template_type.value,
            ],
        )
        assert result.exit_code == 0
        assert "Created configuration file" in result.stdout
        assert expected_title in output_file.read_text()

    @pytest.mark.parametrize(
        "template_type, expected_title",
        [
            (TemplateType.PYTHON, "(Python)"),
            (TemplateType.NODEJS, "(Node.js)"),
            (TemplateType.ELIXIR, "(Elixir)"),
            (TemplateType.JAVA, "(Java with Gradle)"),
            (TemplateType.GO, "(Go)"),
            (TemplateType.RUST, "(Rust)"),
            (TemplateType.TYPESCRIPT, "(TypeScript)"),
            (TemplateType.RUBY, "(Ruby)"),
            (TemplateType.PHP, "(PHP)"),
            (TemplateType.DOTNET, "(C#/.NET)"),
        ],
    )
    def test_config_template_command(
        self,
        template_type: TemplateType,
        expected_title: str,
    ) -> None:
        """Test 'config template' command with different templates."""
        result = runner.invoke(
            app,
            ["config", "template", "--template", template_type.value],
        )
        assert result.exit_code == 0
        assert f"# Veridical Configuration {expected_title}" in result.stdout


@pytest.mark.integration
class TestCliHealCommand:
    def test_heal_dry_run(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test 'heal' dry run mode."""

        async def fake_fetch_issue(*_args: object, **_kwargs: object) -> object:
            from veridical.intake.models import GitHubIssue

            return GitHubIssue(
                owner="o",
                repo="r",
                number=1,
                title="Bug",
                body="Details",
                url="https://github.com/o/r/issues/1",
                labels=["bug"],
                author="alice",
            )

        from veridical.intake.fetcher import IssueFetcher

        monkeypatch.setattr(IssueFetcher, "fetch_issue", fake_fetch_issue)

        result = runner.invoke(
            app,
            ["heal", "--repo", "o/r", "--issue", "1", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Dry run" in result.stdout
        assert "Generated task description" in result.stdout
