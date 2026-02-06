# supervisor Specification

## Purpose
TBD - created by archiving change scaffold-foundation. Update Purpose after archive.
## Requirements
### Requirement: Supervisor Module Structure

The system SHALL provide a `veridical.supervisor` module with the foundational structure for the main control loop.

#### Scenario: Module Import

WHEN importing `from veridical.supervisor import Supervisor`
THEN the import SHALL succeed without errors

#### Scenario: Supervisor Interface

WHEN instantiating the Supervisor class
THEN it SHALL accept a `config` parameter of type `VeridicalConfig`
AND it SHALL expose an async `run(task_description: str) -> LoopResult` method

### Requirement: State Machine Definition

The system SHALL define a `SupervisorState` enum representing all valid loop states.

#### Scenario: State Enumeration

WHEN accessing `SupervisorState`
THEN it SHALL contain the following values: `IDLE`, `DISPATCHING`, `POLLING`, `SYNCING`, `VERIFYING`, `SUCCESS`, `FAILED`

#### Scenario: State Transitions

WHEN the Supervisor transitions between states
THEN it SHALL emit a structured log entry containing `from_state`, `to_state`, and `iteration`

### Requirement: Circuit Breaker Interface

The system SHALL provide a `CircuitBreaker` class that prevents runaway loops.

#### Scenario: Circuit Breaker Initialization

WHEN instantiating `CircuitBreaker`
THEN it SHALL accept `max_iterations: int`, `max_consecutive_failures: int`, and `stagnation_threshold: int` parameters

#### Scenario: Circuit Open Check

WHEN calling `circuit_breaker.is_open()`
THEN it SHALL return `True` if any circuit condition is met
AND it SHALL return `False` otherwise

### Requirement: Loop Result Model

The system SHALL define a `LoopResult` model capturing the outcome of a supervisor run.

#### Scenario: Success Result

WHEN the loop completes successfully
THEN `LoopResult.success` SHALL be `True`
AND `LoopResult.iterations` SHALL contain the count of iterations performed
AND `LoopResult.final_commit` SHALL contain the git commit hash

#### Scenario: Failure Result

WHEN the loop fails or circuit breaks
THEN `LoopResult.success` SHALL be `False`
AND `LoopResult.error_context` SHALL contain the last error message
AND `LoopResult.failure_reason` SHALL describe why the loop terminated

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

### Requirement: Circuit Breaker
The `Supervisor` SHALL terminate the loop if progress is stalled.

#### Scenario: Max Iterations Reached
- **GIVEN** the loop has run `max_iterations` times
- **WHEN** verification fails again
- **THEN** the loop must terminate with `Result.FAILED`
- **AND** the reason must indicate "Max iterations reached"

#### Scenario: Stagnation Detection
- **GIVEN** the agent produces the exact same code patch for `stagnation_threshold` consecutive iterations
- **WHEN** the synchronizer reports duplicate diff hashes
- **THEN** the loop must terminate with `Result.FAILED`

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

