"""Tests for configuration loading and schema."""

from pathlib import Path

import pytest
import yaml

from veridical.config.defaults import (
    DOTNET_CONFIG_TEMPLATE,
    ELIXIR_CONFIG_TEMPLATE,
    GO_CONFIG_TEMPLATE,
    JAVA_CONFIG_TEMPLATE,
    NODEJS_CONFIG_TEMPLATE,
    PHP_CONFIG_TEMPLATE,
    PYTHON_CONFIG_TEMPLATE,
    RUBY_CONFIG_TEMPLATE,
    RUST_CONFIG_TEMPLATE,
    TYPESCRIPT_CONFIG_TEMPLATE,
    TemplateType,
    get_config_template,
)
from veridical.config.loader import (
    find_config_file,
    generate_config_template,
    load_config,
    load_yaml_config,
)
from veridical.config.schema import (
    GitConfig,
    JulesConfig,
    QualityGate,
    SupervisorConfig,
    VeridicalConfig,
    VerifierConfig,
)
from veridical.exceptions import ConfigurationError


@pytest.mark.unit
class TestQualityGate:
    """Tests for QualityGate model."""

    def test_basic_creation(self) -> None:
        """Test basic quality gate creation."""
        gate = QualityGate(name="pytest", command="pytest")
        assert gate.name == "pytest"
        assert gate.command == "pytest"
        assert gate.timeout == 300
        assert gate.required is True

    def test_custom_values(self) -> None:
        """Test quality gate with custom values."""
        gate = QualityGate(
            name="slow-test",
            command="pytest --slow",
            timeout=600,
            required=False,
        )
        assert gate.timeout == 600
        assert gate.required is False


@pytest.mark.unit
class TestJulesConfig:
    """Tests for JulesConfig model."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = JulesConfig()
        assert config.api_base_url == "https://jules.googleapis.com/v1alpha"
        assert config.poll_interval == 30
        assert config.auto_approve_plans is True


@pytest.mark.unit
class TestVeridicalConfig:
    """Tests for VeridicalConfig model."""

    def test_defaults(self) -> None:
        """Test default configuration."""
        config = VeridicalConfig()
        assert isinstance(config.jules, JulesConfig)
        assert isinstance(config.supervisor, SupervisorConfig)
        assert isinstance(config.verifier, VerifierConfig)
        assert isinstance(config.git, GitConfig)

    def test_custom_values(self) -> None:
        """Test configuration with custom values."""
        config = VeridicalConfig(
            jules=JulesConfig(poll_interval=60),
            supervisor=SupervisorConfig(max_iterations=5),
        )
        assert config.jules.poll_interval == 60
        assert config.supervisor.max_iterations == 5


@pytest.mark.unit
class TestConfigLoading:
    """Tests for configuration loading."""

    def test_find_config_file_yaml(self, temp_dir: Path) -> None:
        """Test finding .veridical.yaml file."""
        config_file = temp_dir / ".veridical.yaml"
        config_file.write_text("jules:\n  poll_interval: 60\n")

        found = find_config_file(temp_dir)
        assert found == config_file

    def test_find_config_file_yml(self, temp_dir: Path) -> None:
        """Test finding .veridical.yml file."""
        config_file = temp_dir / ".veridical.yml"
        config_file.write_text("jules:\n  poll_interval: 60\n")

        found = find_config_file(temp_dir)
        assert found == config_file

    def test_find_config_file_not_found(self, temp_dir: Path) -> None:
        """Test when no config file exists."""
        found = find_config_file(temp_dir)
        assert found is None

    def test_load_yaml_config(self, temp_dir: Path) -> None:
        """Test loading YAML configuration."""
        config_file = temp_dir / ".veridical.yaml"
        config_file.write_text("jules:\n  poll_interval: 60\n")

        data = load_yaml_config(config_file)
        assert data["jules"]["poll_interval"] == 60

    def test_load_yaml_config_invalid(self, temp_dir: Path) -> None:
        """Test loading invalid YAML."""
        config_file = temp_dir / ".veridical.yaml"
        config_file.write_text("invalid: yaml: content:")

        with pytest.raises(ConfigurationError):
            load_yaml_config(config_file)

    def test_load_config_with_file(self, sample_config_path: Path) -> None:
        """Test loading config from file."""
        config = load_config(sample_config_path)
        assert config.jules.poll_interval == 30
        assert config.supervisor.max_iterations == 10

    def test_load_config_defaults(self) -> None:
        """Test loading config with defaults when no file."""
        config = load_config(require_file=False)
        assert config.jules.poll_interval == 30  # default value

    def test_load_config_require_file(self, temp_dir: Path) -> None:
        """Test requiring config file when not present."""
        original_dir = Path.cwd()
        import os

        os.chdir(temp_dir)
        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_config(require_file=True)
            assert "not found" in str(exc_info.value).lower()
        finally:
            os.chdir(original_dir)


@pytest.mark.unit
class TestConfigTemplate:
    """Tests for configuration template generation."""

    @pytest.mark.parametrize(
        "template_type, expected_content",
        [
            (TemplateType.PYTHON, PYTHON_CONFIG_TEMPLATE),
            (TemplateType.NODEJS, NODEJS_CONFIG_TEMPLATE),
            (TemplateType.ELIXIR, ELIXIR_CONFIG_TEMPLATE),
            (TemplateType.JAVA, JAVA_CONFIG_TEMPLATE),
            (TemplateType.GO, GO_CONFIG_TEMPLATE),
            (TemplateType.RUST, RUST_CONFIG_TEMPLATE),
            (TemplateType.TYPESCRIPT, TYPESCRIPT_CONFIG_TEMPLATE),
            (TemplateType.RUBY, RUBY_CONFIG_TEMPLATE),
            (TemplateType.PHP, PHP_CONFIG_TEMPLATE),
            (TemplateType.DOTNET, DOTNET_CONFIG_TEMPLATE),
        ],
    )
    def test_get_template(
        self,
        template_type: TemplateType,
        expected_content: str,
    ) -> None:
        """Test getting specific config templates."""
        template = get_config_template(template_type)
        assert template == expected_content

    def test_get_template_default(self) -> None:
        """Test getting default config template (Python)."""
        template = get_config_template()
        assert template == PYTHON_CONFIG_TEMPLATE

    def test_generate_template(self, temp_dir: Path) -> None:
        """Test generating template file."""
        output = temp_dir / ".veridical.yaml"
        result = generate_config_template(output)
        assert result == output
        assert output.exists()
        assert "jules:" in output.read_text()

    @pytest.mark.parametrize(
        "template_type, expected_gates, expected_title",
        [
            (
                TemplateType.PYTHON,
                ["pytest", "ruff-check", "ruff-format", "mypy"],
                "(Python)",
            ),
            (
                TemplateType.NODEJS,
                ["npm-test", "eslint", "prettier"],
                "(Node.js)",
            ),
            (
                TemplateType.ELIXIR,
                ["mix-test", "mix-credo", "mix-format", "mix-dialyzer"],
                "(Elixir)",
            ),
            (
                TemplateType.JAVA,
                ["gradle-test", "gradle-checkstyle"],
                "(Java with Gradle)",
            ),
            (
                TemplateType.GO,
                ["go-test", "go-vet", "golangci-lint", "go-fmt"],
                "(Go)",
            ),
            (
                TemplateType.RUST,
                ["cargo-test", "cargo-clippy", "cargo-fmt"],
                "(Rust)",
            ),
            (
                TemplateType.TYPESCRIPT,
                ["npm-test", "tsc", "eslint", "prettier"],
                "(TypeScript)",
            ),
            (TemplateType.RUBY, ["rspec", "rubocop"], "(Ruby)"),
            (
                TemplateType.PHP,
                ["phpunit", "phpstan", "php-cs-fixer"],
                "(PHP)",
            ),
            (
                TemplateType.DOTNET,
                ["dotnet-test", "dotnet-format", "dotnet-build"],
                "(C#/.NET)",
            ),
        ],
    )
    def test_generate_specific_template(
        self,
        temp_dir: Path,
        template_type: TemplateType,
        expected_gates: list[str],
        expected_title: str,
    ) -> None:
        """Test generating specific language template files."""
        output = temp_dir / f".veridical.{template_type.value}.yaml"
        generate_config_template(output, template=template_type)

        assert output.exists()
        content = output.read_text()
        assert f"# Veridical Configuration {expected_title}" in content

        # Verify quality gates
        config_data = yaml.safe_load(content)
        gate_names = [
            gate["name"] for gate in config_data.get("verifier", {}).get("quality_gates", [])
        ]
        assert gate_names == expected_gates

    def test_generate_template_exists(self, temp_dir: Path) -> None:
        """Test generating template when file exists."""
        output = temp_dir / ".veridical.yaml"
        output.write_text("existing content")

        with pytest.raises(ConfigurationError) as exc_info:
            generate_config_template(output)
        assert "already exists" in str(exc_info.value).lower()

    def test_generate_template_force(self, temp_dir: Path) -> None:
        """Test force overwriting template."""
        output = temp_dir / ".veridical.yaml"
        output.write_text("existing content")

        generate_config_template(output, force=True)
        assert "jules:" in output.read_text()
