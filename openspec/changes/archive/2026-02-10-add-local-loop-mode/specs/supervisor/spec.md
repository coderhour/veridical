## ADDED Requirements

### Requirement: Local Supervisor Loop
The system SHALL provide a `LocalSupervisor` class that orchestrates a local verify-and-fix cycle without requiring a remote AI agent.

#### Scenario: Local Loop Execution
- **WHEN** `LocalSupervisor.run(task_description)` is called
- **THEN** it SHALL execute the configured worker command
- **AND** run all quality gates via the existing `Verifier`
- **AND** loop until all gates pass or the circuit breaker trips

#### Scenario: Error Context Feedback
- **GIVEN** a verification iteration fails
- **WHEN** the next worker invocation starts
- **THEN** the system SHALL pass the verification error context to the worker
- **AND** the error context SHALL be available via the `VERIDICAL_ERROR_CONTEXT` environment variable

#### Scenario: Circuit Breaker Integration
- **WHEN** the local loop exceeds `max_iterations` or `max_consecutive_failures`
- **THEN** the `CircuitBreaker` SHALL trip and terminate the loop
- **AND** the result SHALL indicate the termination reason

#### Scenario: Work Log Integration
- **WHEN** the local loop completes an iteration
- **THEN** it SHALL record the iteration in the work log
- **AND** the entry SHALL include worker exit code, verification result, and duration

### Requirement: Local Runner Component
The system SHALL provide a `LocalRunner` class that executes a shell command as the AI worker.

#### Scenario: Subprocess Execution
- **WHEN** `LocalRunner.run(task, error_context)` is called in subprocess mode
- **THEN** it SHALL execute the configured `worker_command` as a subprocess
- **AND** it SHALL capture stdout and stderr
- **AND** it SHALL return the exit code

#### Scenario: Interactive Execution
- **WHEN** `LocalRunner.run(task, error_context)` is called in interactive mode
- **THEN** it SHALL execute the worker command attached to the current TTY
- **AND** it SHALL wait for the command to complete
- **AND** it SHALL return the exit code without capturing output

#### Scenario: Worker Timeout
- **WHEN** the worker command exceeds `worker_timeout` seconds
- **THEN** the system SHALL terminate the worker process
- **AND** return a timeout error result
