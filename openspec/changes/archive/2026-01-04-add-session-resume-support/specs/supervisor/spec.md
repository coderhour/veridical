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

#### Scenario: Resume Patch Application Failure

- **GIVEN** a session ID is provided to `run()`
- **WHEN** the patch from the resumed session fails to apply
- **THEN** it SHALL abort immediately with a FAILED result
- **AND** it SHALL NOT create a new session for retry
- **AND** the failure reason SHALL indicate the patch failed
- **AND** the error context SHALL explain that local code has diverged

#### Scenario: Invalid Session ID

- **GIVEN** an invalid or non-existent session ID is provided to `run()`
- **WHEN** the API returns an error (e.g., 404 Not Found)
- **THEN** it SHALL abort immediately with a FAILED result
- **AND** the failure reason SHALL indicate "Invalid session ID"
- **AND** the error context SHALL include the provided session ID
- **AND** the error context SHALL explain the session could not be found
