"""Integration tests for the CLI."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from veridical.cli import app
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
