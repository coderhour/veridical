# supervisor Spec Delta

## MODIFIED Requirements

### Requirement: Autonomous Control Loop

The `Supervisor.run()` method SHALL support resuming from an existing session.

#### Scenario: Resume Existing Session

- **GIVEN** a valid session ID is provided to `run()`
- **WHEN** the supervisor starts the first iteration
- **THEN** it SHALL skip the DISPATCHING state
- **AND** it SHALL proceed directly to POLLING with the provided session ID
- **AND** it SHALL continue with SYNCING, VERIFYING, and loop logic as normal

#### Scenario: Resume Then Iterate

- **GIVEN** a session ID is provided and the first iteration fails verification
- **WHEN** the loop continues to iteration 2
- **THEN** it SHALL create a new session (normal DISPATCHING behavior)
- **AND** the provided session ID SHALL NOT be reused

#### Scenario: Run Interface Extension

WHEN calling `Supervisor.run()`
THEN it SHALL accept an optional `session_id: str | None` parameter
AND it SHALL default to `None` (create new session behavior)
