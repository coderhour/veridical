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
- **WHEN** loading configuration
- **THEN** `VeridicalConfig` SHALL contain the following sections:
  - `jules`: Jules API configuration
  - `supervisor`: Loop control settings
  - `verifier`: Quality gate configuration
  - `git`: Git operation settings
  - `local_llm`: Local LLM settings (Optional)

#### Scenario: Rules Config Section
- **WHEN** accessing `config.jules`
- **THEN** it SHALL contain `api_base_url: str` (default: `https://jules.googleapis.com/v1alpha`)
- **AND** it SHALL contain `poll_interval: int` (default: 30)
- **AND** it SHALL contain `poll_timeout: int` (default: 3600)
- **AND** it SHALL contain `auto_approve_plans: bool` (default: True)

#### Scenario: Supervisor Config Section
- **WHEN** accessing `config.supervisor`
- **THEN** it SHALL contain `max_iterations: int` (default: 10)
- **AND** it SHALL contain `max_consecutive_failures: int` (default: 3)
- **AND** it SHALL contain `stagnation_threshold: int` (default: 3)

#### Scenario: Verifier Config Section
- **WHEN** accessing `config.verifier`
- **THEN** it SHALL contain `quality_gates: list[QualityGate]`
- **AND** each `QualityGate` SHALL have `name: str` and `type: str` (default: `command`)
- **AND** `QualityGate` SHALL support types: `command`, `task_completion`, `assertion`, `diff_scope`, `composite`
- **AND** `QualityGate` SHALL support optional fields: `warn_only: bool`, `when_files_changed: list[str]`, `exit_code_map: dict[int, str]`
- **AND** it SHALL contain `feedback_mode: str` (default: `auto`)

#### Scenario: Git Config Section
- **WHEN** accessing `config.git`
- **THEN** it SHALL contain `base_branch: str` (default: `main`)
- **AND** it SHALL contain `branch_prefix: str` (default: `veridical/iter-`)

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
THEN the system SHALL return `python`, `nodejs`, `elixir`, `java`, `go`, `rust`, `typescript`, `ruby`, `php`, `dotnet`

### Requirement: Go Template

The system SHALL provide a Go-specific configuration template.

#### Scenario: Go Template Content

WHEN generating a template for `go`
THEN it SHALL include quality gates for `go test ./...`, `go vet ./...`, `golangci-lint run`, and `gofmt -l .`
AND it SHALL use appropriate timeouts for Go tooling

### Requirement: Rust Template

The system SHALL provide a Rust-specific configuration template.

#### Scenario: Rust Template Content

WHEN generating a template for `rust`
THEN it SHALL include quality gates for `cargo test`, `cargo clippy -- -D warnings`, and `cargo fmt --check`
AND it SHALL use appropriate timeouts for Rust tooling

### Requirement: TypeScript Template

The system SHALL provide a TypeScript-specific configuration template.

#### Scenario: TypeScript Template Content

WHEN generating a template for `typescript`
THEN it SHALL include quality gates for `npm test`, `tsc --noEmit`, `eslint .`, and `prettier --check .`
AND it SHALL include type checking via TypeScript compiler

### Requirement: Ruby Template

The system SHALL provide a Ruby-specific configuration template.

#### Scenario: Ruby Template Content

WHEN generating a template for `ruby`
THEN it SHALL include quality gates for `bundle exec rspec` and `bundle exec rubocop`
AND it SHALL use appropriate timeouts for Ruby tooling

### Requirement: PHP Template

The system SHALL provide a PHP-specific configuration template.

#### Scenario: PHP Template Content

WHEN generating a template for `php`
THEN it SHALL include quality gates for `./vendor/bin/phpunit`, `./vendor/bin/phpstan analyse`, and `./vendor/bin/php-cs-fixer fix --dry-run --diff`
AND it SHALL use Composer-based tooling paths

### Requirement: .NET Template

The system SHALL provide a .NET-specific configuration template.

#### Scenario: .NET Template Content

WHEN generating a template for `dotnet`
THEN it SHALL include quality gates for `dotnet test`, `dotnet format --verify-no-changes`, and `dotnet build --warnaserror`
AND it SHALL use appropriate timeouts for .NET tooling

### Requirement: Auto Create Work Branch Configuration

The system SHALL support configuration for automatic work branch creation.

#### Scenario: Default Enabled

WHEN `git.auto_create_work_branch` is not specified in config
THEN it SHALL default to `true`
AND Veridical SHALL create a work branch for each run

#### Scenario: Explicitly Disabled

WHEN `git.auto_create_work_branch` is set to `false`
THEN Veridical SHALL use legacy behavior (merge to `base_branch`)
AND no work branch SHALL be created

#### Scenario: Environment Variable Override

WHEN environment variable `VERIDICAL_GIT__AUTO_CREATE_WORK_BRANCH` is set to `false`
THEN it SHALL override any file-based configuration
AND Veridical SHALL use legacy merge behavior

### Requirement: Local LLM Configuration
The system SHALL support configuring a local LLM endpoint.

#### Scenario: Local LLM Section
- **WHEN** accessing `config.local_llm`
- **THEN** it SHALL support `base_url: str` (default: `http://localhost:11434/v1`)
- **AND** it SHALL support `model: str` (default: `qwen2.5-coder`)
- **AND** it SHALL support `timeout: int` (default: 60)

### Requirement: gtr Worktree Configuration
The system SHALL support configuration fields for gtr worktree integration in the `local` config section.

#### Scenario: gtr Enabled Field
- **WHEN** accessing `config.local`
- **THEN** it SHALL contain `gtr_enabled: bool` (default: `False`)
- **AND** when `true`, the local supervisor SHALL create a git worktree for each run

#### Scenario: gtr Auto-Cleanup Field
- **WHEN** accessing `config.local`
- **THEN** it SHALL contain `gtr_auto_cleanup: bool` (default: `True`)
- **AND** when `true`, the worktree SHALL be removed after a successful run
- **AND** when `false`, the worktree SHALL be preserved after completion regardless of outcome

#### Scenario: Environment Variable Override for gtr
- **WHEN** environment variable `VERIDICAL_LOCAL__GTR_ENABLED` is set to `true`
- **THEN** it SHALL override the file-based `local.gtr_enabled` configuration
- **AND** gtr worktree isolation SHALL be enabled

### Requirement: Local Provider Configuration
The system SHALL support a `local.provider` configuration field for selecting a named local provider preset.

#### Scenario: Provider Config Field
- **WHEN** accessing `config.local`
- **THEN** it SHALL contain `provider: str | None` (default: `None`)
- **AND** when set, the provider preset SHALL auto-configure `worker_command`, `mode`, and error delivery strategy

#### Scenario: Provider Overrides Worker Command
- **WHEN** `local.provider` is set to a valid provider name (e.g., `claude-code`)
- **AND** `local.worker_command` is empty
- **THEN** the system SHALL use the provider's default command configuration
- **AND** the provider's error delivery strategy SHALL be used instead of the default env var

#### Scenario: Worker Command Takes Precedence
- **WHEN** both `local.provider` and `local.worker_command` are set
- **THEN** `local.worker_command` SHALL take precedence over the provider's default command
- **AND** the provider's error delivery strategy SHALL still be used

#### Scenario: Unknown Provider Name
- **WHEN** `local.provider` is set to an unregistered provider name
- **THEN** the system SHALL raise a `ConfigurationError` listing available providers

### Requirement: Local Provider Registry
The system SHALL maintain a registry of named local provider presets.

#### Scenario: Built-in Providers
- **WHEN** querying available providers
- **THEN** the registry SHALL include `claude-code` and `gemini-cli`
- **AND** each provider SHALL expose its detection status (whether the tool is available on PATH)

#### Scenario: Provider Registration
- **WHEN** registering a new provider
- **THEN** the registry SHALL accept a provider name and a class implementing the `LocalProvider` protocol
- **AND** duplicate names SHALL overwrite the previous registration

#### Scenario: Provider Listing
- **WHEN** listing available providers
- **THEN** the system SHALL return provider names, descriptions, and detection status

### Requirement: Report Configuration
The system SHALL support a `report` configuration section for report generation settings.

#### Scenario: Report Config Section
- **WHEN** accessing `config.report`
- **THEN** it SHALL contain `default_format: str` (default: `terminal`, options: `terminal`, `json`, `html`)
- **AND** it SHALL contain `html_template: str | None` (default: `None`, path to custom Jinja2 template)

#### Scenario: Report Config Defaults
- **WHEN** no `report` section is specified in `.veridical.yaml`
- **THEN** the system SHALL use default values
- **AND** reports SHALL render in terminal format by default

### Requirement: Worker Backend Configuration
The system SHALL support selecting and configuring the active worker backend.

#### Scenario: Worker Config Section
- **WHEN** accessing `config.worker`
- **THEN** it SHALL contain `backend: str` (default: `jules`)
- **AND** it SHALL contain backend-specific configuration nested under the backend name

#### Scenario: Default Backend
- **WHEN** `worker.backend` is not specified
- **THEN** it SHALL default to `jules`
- **AND** the system SHALL construct a `JulesWorker` using existing Jules configuration

#### Scenario: Unknown Backend
- **WHEN** `worker.backend` is set to an unregistered backend name
- **THEN** the system SHALL raise a `ConfigurationError` listing available backends

### Requirement: Local Mode Configuration
The system SHALL support a `local` configuration section for the local verify-and-loop mode.

#### Scenario: Local Config Section
- **WHEN** accessing `config.local`
- **THEN** it SHALL contain `worker_command: str` (default: `""`)
- **AND** it SHALL contain `worker_timeout: int` (default: `600`)
- **AND** it SHALL contain `mode: str` (default: `subprocess`, options: `subprocess`, `interactive`)
- **AND** it SHALL contain `error_env_var: str` (default: `VERIDICAL_ERROR_CONTEXT`)

#### Scenario: Local Config Validation
- **WHEN** `veri local` is invoked
- **AND** `local.worker_command` is empty and no `--worker` flag is provided
- **THEN** it SHALL raise a `ConfigurationError` with instructions to set the worker command

#### Scenario: Local Config in Template
- **WHEN** generating a config template
- **THEN** it SHALL include a commented `local` section with example worker commands for common tools (e.g., `aider`, `claude-code`, custom scripts)

