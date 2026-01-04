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

