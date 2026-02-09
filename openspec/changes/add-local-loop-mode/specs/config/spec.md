## ADDED Requirements

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
