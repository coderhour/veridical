"""Tests for configuration loading and schema."""

from pathlib import Path

import pytest

from veridical.config.defaults import get_config_template
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

    def test_get_template_default(self) -> None:
        """Test getting the default 'python' config template."""
        template = get_config_template()  # Defaults to python
        assert "jules:" in template
        assert "supervisor:" in template
        assert "verifier:" in template
        assert "git:" in template
        assert "quality_gates:" in template
        assert "pytest" in template

    def test_get_template_explicit_python(self) -> None:
        """Test explicitly getting the 'python' config template."""
        template = get_config_template("python")
        assert "pytest" in template
        assert "ruff" in template
        assert "mypy" in template

    def test_get_template_generic(self) -> None:
        """Test getting the 'default' config template."""
        template = get_config_template("default")
        assert "quality_gates: []" in template

    def test_get_template_not_found(self) -> None:
        """Test requesting a non-existent template."""
        with pytest.raises(ConfigurationError) as exc_info:
            get_config_template("nonexistent")
        assert "not found" in str(exc_info.value).lower()

    def test_generate_template_default(self, temp_dir: Path) -> None:
        """Test generating the default template file."""
        output = temp_dir / ".veridical.yaml"
        result = generate_config_template(output)
        assert result == output
        assert output.exists()
        assert "pytest" in output.read_text()

    def test_generate_template_with_name(self, temp_dir: Path) -> None:
        """Test generating a template by name."""
        output = temp_dir / ".veridical.yaml"
        generate_config_template(output, template="default")
        assert "quality_gates: []" in output.read_text()

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
