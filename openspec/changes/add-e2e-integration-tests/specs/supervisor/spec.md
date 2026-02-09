## ADDED Requirements

### Requirement: End-to-End Test Coverage
The system SHALL have end-to-end tests that exercise the full supervisor loop against mock workers.

#### Scenario: Happy Path Full Loop
- **GIVEN** a mock worker that produces a patch passing all quality gates
- **WHEN** the supervisor loop runs
- **THEN** it SHALL complete with SUCCESS on the first iteration
- **AND** the final commit SHALL exist on the work branch

#### Scenario: Retry After Verification Failure
- **GIVEN** a mock worker that produces a failing patch on iteration 1 and a passing patch on iteration 2
- **WHEN** the supervisor loop runs
- **THEN** it SHALL complete with SUCCESS after 2 iterations
- **AND** error context from iteration 1 SHALL be passed to the worker for iteration 2

#### Scenario: Circuit Breaker Trip
- **GIVEN** a mock worker that always produces failing patches
- **WHEN** the supervisor loop runs with `max_iterations: 3`
- **THEN** it SHALL terminate with FAILED after 3 iterations
- **AND** the failure reason SHALL indicate "Max iterations reached"

#### Scenario: Stagnation Detection
- **GIVEN** a mock worker that produces identical patches on every iteration
- **WHEN** the supervisor loop runs with `stagnation_threshold: 2`
- **THEN** it SHALL terminate with FAILED
- **AND** the failure reason SHALL indicate stagnation

#### Scenario: State Persistence Round-Trip
- **GIVEN** a supervisor loop that is interrupted after iteration 1
- **WHEN** the loop is resumed with `resume_from_state=True`
- **THEN** it SHALL restore the session ID and iteration count
- **AND** continue from the saved state

### Requirement: Test Infrastructure
The system SHALL provide reusable test fixtures for E2E and integration testing.

#### Scenario: Mock Worker Fixture
- **WHEN** tests require a mock AI worker
- **THEN** a `MockJulesClient` fixture SHALL be available
- **AND** it SHALL support configuring deterministic patch responses per iteration

#### Scenario: Temporary Git Repository Fixture
- **WHEN** tests require git operations
- **THEN** a temporary git repository fixture SHALL be available
- **AND** it SHALL be initialized with a baseline commit and configured remote
