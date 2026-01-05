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

#### Scenario: Git Config Section

WHEN accessing `config.git`
THEN it SHALL contain `base_branch: str` (default: `main`)
AND it SHALL contain `branch_prefix: str` (default: `veridical/iter-`)
AND it SHALL contain `auto_cleanup: bool` (default: `true`)
AND it SHALL contain `auto_create_work_branch: bool` (default: `true`)

> **Delta**: Added `auto_create_work_branch` field with `true` as default.

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

