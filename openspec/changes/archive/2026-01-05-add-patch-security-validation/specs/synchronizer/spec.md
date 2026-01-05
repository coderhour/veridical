## ADDED Requirements

### Requirement: Patch Scope Validation
The system SHALL validate patches against configurable scope rules before application.

#### Scenario: Denylist Violation in Strict Mode
- **WHEN** a patch modifies a file matching the denylist (e.g., `.github/workflows/`)
- **AND** `strict_mode` is `true`
- **THEN** the patch SHALL be rejected
- **AND** `PatchResult.status` SHALL be `SCOPE_VIOLATION`
- **AND** the error SHALL list all violated files

#### Scenario: Denylist Violation in Warning Mode
- **WHEN** a patch modifies a file matching the denylist
- **AND** `strict_mode` is `false`
- **THEN** the patch SHALL be applied
- **AND** a warning SHALL be logged listing violated files

#### Scenario: Allowlist Override
- **WHEN** a file matches both allowlist and denylist patterns
- **THEN** the allowlist SHALL take precedence
- **AND** the file SHALL be allowed

#### Scenario: Clean Patch Validation
- **WHEN** a patch modifies only files not matching the denylist
- **THEN** validation SHALL pass
- **AND** the patch SHALL proceed to application

### Requirement: Security Audit Logging
The system SHALL log all patch operations for security audit.

#### Scenario: Patch Application Logged
- **WHEN** a patch is successfully applied
- **THEN** the system SHALL log all modified file paths
- **AND** the log entry SHALL include session ID and iteration number

#### Scenario: Rejected Patch Logged
- **WHEN** a patch is rejected due to scope violation
- **THEN** the system SHALL log the rejection at WARNING level
- **AND** the log SHALL include violated patterns and file paths
- **AND** the log SHALL include session ID for traceability

### Requirement: Default Security Denylist
The system SHALL provide a default denylist of sensitive file patterns.

#### Scenario: Default Denylist Contents
- **WHEN** no custom denylist is configured
- **THEN** the default denylist SHALL include:
  - `.github/**`
  - `.gitlab-ci.yml`
  - `AGENTS.md`
  - `*.env`
  - `.veridical.yaml`
  - `Dockerfile`
  - `docker-compose*.yml`
