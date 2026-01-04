# Dispatcher Specification

## ADDED Requirements

### Requirement: Git Repo Auto-Detection
The `Dispatcher` SHALL automatically determine the target repository from the local environment.

#### Scenario: Valid Git Remote
- **GIVEN** the current directory is a git repository with remote `origin` set to `git@github.com:veridical/veridical.git`
- **WHEN** `create_session` is called without explicit source
- **THEN** it must use `sources/github/veridical/veridical` as the `source`

#### Scenario: No Git Remote
- **GIVEN** the current directory is not a git repository
- **WHEN** `create_session` is called without explicit source
- **THEN** it must raise a `ConfigurationError`

### Requirement: Dynamic Constraint Injection
The `Dispatcher` SHALL inject verification feedback into the prompt for subsequent iterations.

#### Scenario: Prompt Construction with Error
- **GIVEN** an `error_context` containing "AssertionError: expected 5 got 3"
- **WHEN** `build_prompt` is called
- **THEN** it must include a section "EPHEMERAL CONSTRAINTS"
- **AND** it must include the error text
