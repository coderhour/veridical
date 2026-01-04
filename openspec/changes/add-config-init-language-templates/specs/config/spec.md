## MODIFIED Requirements

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

## ADDED Requirements

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
