## ADDED Requirements

### Requirement: Loop State Persistence
The system SHALL persist loop state to enable resumption after interruption.

#### Scenario: State File Creation
- **WHEN** the supervisor loop starts an iteration
- **THEN** it SHALL save current state to `.veridical_state.json`
- **AND** the state SHALL include iteration count, session ID, error context, and work branch

#### Scenario: State Restoration
- **WHEN** `veri resume` is invoked
- **AND** a valid `.veridical_state.json` exists
- **THEN** the supervisor SHALL restore the saved state
- **AND** continue from the last saved iteration

#### Scenario: State File Cleanup
- **WHEN** the supervisor loop completes successfully
- **THEN** it SHALL delete the `.veridical_state.json` file
- **AND** log that state has been cleared

### Requirement: Graceful Shutdown
The system SHALL handle interruption signals gracefully.

#### Scenario: SIGINT Handling
- **WHEN** SIGINT (Ctrl+C) is received during loop execution
- **THEN** the system SHALL save current state to disk
- **AND** clean up the current iteration branch
- **AND** return to the starting branch
- **AND** exit with a non-zero status code

#### Scenario: SIGTERM Handling
- **WHEN** SIGTERM is received during loop execution
- **THEN** the system SHALL behave identically to SIGINT handling

#### Scenario: Double Signal Force Exit
- **WHEN** a second interrupt signal is received within 3 seconds
- **THEN** the system SHALL exit immediately without cleanup
- **AND** log a warning about unclean shutdown
