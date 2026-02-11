## ADDED Requirements

### Requirement: Parallel Orchestration Configuration
The system SHALL support a `parallel` configuration section for multi-agent parallel execution settings.

#### Scenario: Parallel Config Section
- **WHEN** accessing `config.parallel`
- **THEN** it SHALL contain `max_workers: int` (default: `3`, maximum concurrent worker instances)
- **AND** it SHALL contain `merge_strategy: str` (default: `sequential`, options: `sequential`)
- **AND** it SHALL contain `final_verification: bool` (default: `True`, whether to run integrated verification after merge)

#### Scenario: Parallel Config Defaults
- **WHEN** no `parallel` section is specified in `.veridical.yaml`
- **THEN** the system SHALL use default values
- **AND** `veri parallel` SHALL function with defaults when invoked

#### Scenario: Max Workers Validation
- **WHEN** `parallel.max_workers` is set to a value less than 1 or greater than 10
- **THEN** the system SHALL raise a `ConfigurationError` with the valid range

#### Scenario: Parallel Config in Template
- **WHEN** generating a config template
- **THEN** it SHALL include a commented `parallel` section with `max_workers`, `merge_strategy`, and `final_verification` fields
