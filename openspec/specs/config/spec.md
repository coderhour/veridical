# config Specification

## Purpose
TBD - created by archiving change scaffold-foundation. Update Purpose after archive.
## Requirements
### Requirement: Config Module Structure

The system SHALL provide a `veridical.config` module for configuration management.

#### Scenario: Module Import

WHEN importing `from veridical.config import VeridicalConfig, load_config`
THEN the import SHALL succeed without errors

### Requirement: Configuration Schema

The system SHALL define a `VeridicalConfig` Pydantic model.

#### Scenario: Config Structure

WHEN loading configuration
THEN `VeridicalConfig` SHALL contain the following sections:
- `jules`: Jules API configuration
- `supervisor`: Loop control settings
- `verifier`: Quality gate configuration
- `git`: Git operation settings

#### Scenario: Jules Config Section

WHEN accessing `config.jules`
THEN it SHALL contain `api_base_url: str` (default: `https://jules.googleapis.com/v1alpha`)
AND it SHALL contain `poll_interval: int` (default: 30)
AND it SHALL contain `poll_timeout: int` (default: 3600)
AND it SHALL contain `auto_approve_plans: bool` (default: True)

#### Scenario: Supervisor Config Section

WHEN accessing `config.supervisor`
THEN it SHALL contain `max_iterations: int` (default: 10)
AND it SHALL contain `max_consecutive_failures: int` (default: 3)
AND it SHALL contain `stagnation_threshold: int` (default: 3)

#### Scenario: Verifier Config Section

WHEN accessing `config.verifier`
THEN it SHALL contain `quality_gates: list[QualityGate]`
AND each `QualityGate` SHALL have `name: str` and `command: str`

#### Scenario: Git Config Section

WHEN accessing `config.git`
THEN it SHALL contain `base_branch: str` (default: `main`)
AND it SHALL contain `branch_prefix: str` (default: `veridical/iter-`)

### Requirement: Configuration Loading

The system SHALL load configuration from multiple sources with precedence.

#### Scenario: Load Priority

WHEN loading configuration
THEN environment variables SHALL override config file values
AND config file values SHALL override defaults

#### Scenario: Config File Discovery

WHEN searching for config files
THEN it SHALL look for `.veridical.yaml` in the current directory
AND it SHALL look for `.veridical.yml` as an alternative
AND it SHALL fall back to defaults if no file is found

#### Scenario: Environment Variable Mapping

WHEN environment variable `VERIDICAL_JULES_API_BASE_URL` is set
THEN it SHALL override `config.jules.api_base_url`
AND similar mappings SHALL exist for all config values

### Requirement: API Key Handling

The system SHALL handle API keys securely.

#### Scenario: API Key from Environment

WHEN loading Jules API key
THEN it SHALL read from `JULES_API_KEY` environment variable
AND it SHALL NOT accept API keys from config files

#### Scenario: Missing API Key

WHEN `JULES_API_KEY` is not set
AND a command requires API access
THEN it SHALL raise `ConfigurationError` with clear instructions

### Requirement: Configuration Validation

The system SHALL validate configuration at load time.

#### Scenario: Invalid Value

WHEN a config value fails validation (e.g., negative `max_iterations`)
THEN it SHALL raise `ConfigurationError` with the invalid field and reason

#### Scenario: Unknown Fields

WHEN the config file contains unknown fields
THEN it SHALL log a warning
AND it SHALL ignore the unknown fields

### Requirement: Default Configuration Template

The system SHALL provide language-specific templates for new projects.

#### Scenario: Template Content

WHEN generating a config template
THEN it SHALL contain all available options with comments
AND it SHALL use sensible defaults
AND it SHALL include examples for quality gates

#### Scenario: Python Template

WHEN generating a template for `python`
THEN it SHALL include quality gates for `pytest`, `ruff check`, `ruff format --check`, and `mypy`
AND it SHALL use `src/` as the default source directory

#### Scenario: Node.js Template

WHEN generating a template for `nodejs`
THEN it SHALL include quality gates for `npm test`, `eslint .`, and `prettier --check .`
AND it SHALL use appropriate timeouts for Node.js tooling

#### Scenario: Elixir Template

WHEN generating a template for `elixir`
THEN it SHALL include quality gates for `mix test`, `mix credo --strict`, `mix format --check-formatted`, and `mix dialyzer`
AND it SHALL use appropriate timeouts for Elixir tooling

#### Scenario: Java Template

WHEN generating a template for `java`
THEN it SHALL include quality gates with comments supporting both Gradle and Maven
AND it SHALL include gates for testing and static analysis (checkstyle)
AND it SHALL document how to adapt for each build system

### Requirement: Template Registry

The system SHALL maintain a registry of language-specific configuration templates.

#### Scenario: Supported Templates

WHEN querying supported templates
THEN the system SHALL return `python`, `nodejs`, `elixir`, `java`

#### Scenario: Template Retrieval

WHEN requesting a template by name
THEN the system SHALL return the corresponding configuration template string

#### Scenario: Unknown Template

WHEN requesting an unknown template
THEN the system SHALL raise `ConfigurationError` with list of valid options

