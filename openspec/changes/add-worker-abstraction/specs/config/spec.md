## ADDED Requirements

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
