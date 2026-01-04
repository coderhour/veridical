# Supervisor Specification

## ADDED Requirements

### Requirement: Autonomous Control Loop
The `Supervisor` SHALL orchestrate the quality assurance loop through defined states.

#### Scenario: Successful Iteration
- **GIVEN** a valid task description
- **WHEN** `run()` is called
- **THEN** it must transition from DISPATCHING -> POLLING -> SYNCING -> VERIFYING -> SUCCESS
- **AND** return a `LoopResult` with `success=True`

#### Scenario: Iterative Repair
- **GIVEN** a task that produces failing code in the first attempt
- **WHEN** `Verifier` returns failure
- **THEN** `Supervisor` must capture the error feedback
- **AND** increment the iteration count
- **AND** dispatch a new session with the error context
- **AND** continue until verification passes or max iterations reached

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
