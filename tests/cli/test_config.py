"""Tests for the `veridical config` CLI command."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from veridical.cli.config import config_app
from veridical.config.defaults import CONFIG_TEMPLATES, TemplateName

runner = CliRunner()


def assert_is_template(content: str, template_name: TemplateName) -> None:
    """Assert that content contains key markers for a given template."""
    # Universal markers
    assert "jules:" in content
    assert "api_base_url:" in content
    assert "supervisor:" in content
    assert "git:" in content
    assert "base_branch:" in content

    # Language-specific markers
    if template_name == "python":
        assert "command: pytest" in content
        assert "command: mypy src/" in content
    elif template_name == "nodejs":
        assert "command: npm test" in content
        assert "command: npx eslint ." in content
    elif template_name == "elixir":
        assert "command: mix test" in content
        assert "command: mix credo" in content
    elif template_name == "java":
        assert "command: ./gradlew test" in content
        assert "command: ./gradlew check" in content


@pytest.mark.cli
class TestConfigInitCommand:
    """Tests for the `config init` command."""

    def test_init_default(self, temp_dir: Path) -> None:
        """Test `config init` with default options."""
        output_file = temp_dir / ".veridical.yaml"
        result = runner.invoke(config_app, ["init", "--output", str(output_file)])

        assert result.exit_code == 0
        assert "Created configuration file" in result.stdout
        assert str(output_file) in result.stdout
        assert output_file.exists()
        assert_is_template(output_file.read_text(), "python")

    def test_init_force(self, temp_dir: Path) -> None:
        """Test `config init --force`."""
        output_file = temp_dir / ".veridical.yaml"
        output_file.write_text("old content")

        result = runner.invoke(
            config_app,
            ["init", "--output", str(output_file), "--force"],
        )

        assert result.exit_code == 0
        assert "Created configuration file" in result.stdout
        assert "old content" not in output_file.read_text()

    @pytest.mark.parametrize("template", ["python", "nodejs", "elixir", "java"])
    def test_init_with_template(self, temp_dir: Path, template: TemplateName) -> None:
        """Test `config init` with different templates."""
        output_file = temp_dir / f".veridical.{template}.yaml"
        result = runner.invoke(
            config_app,
            ["init", "--output", str(output_file), "--template", template],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        assert_is_template(output_file.read_text(), template)

    def test_init_unknown_template(self, temp_dir: Path) -> None:
        """Test `config init` with an unknown template."""
        output_file = temp_dir / ".veridical.yaml"
        result = runner.invoke(
            config_app,
            ["init", "--output", str(output_file), "--template", "rust"],
            catch_exceptions=False,
        )
        assert result.exit_code != 0
        # Typer sends error messages for invalid choices to stderr
        assert "Invalid value for '--template' / '-t'" in result.stderr
        assert not output_file.exists()


@pytest.mark.cli
class TestConfigTemplateCommand:
    """Tests for the `config template` command."""

    def test_template_default(self) -> None:
        """Test `config template` with default options."""
        result = runner.invoke(config_app, ["template"])
        assert result.exit_code == 0
        assert_is_template(result.stdout, "python")

    @pytest.mark.parametrize("template", ["python", "nodejs", "elixir", "java"])
    def test_template_with_arg(self, template: TemplateName) -> None:
        """Test `config template` with a specific template."""
        result = runner.invoke(config_app, ["template", "--template", template])
        assert result.exit_code == 0
        assert_is_template(result.stdout, template)

    def test_template_unknown(self) -> None:
        """Test `config template` with an unknown template."""
        result = runner.invoke(
            config_app,
            ["template", "--template", "cobol"],
            catch_exceptions=False,
        )
        assert result.exit_code != 0
        assert "Invalid value for '--template' / '-t'" in result.stderr
