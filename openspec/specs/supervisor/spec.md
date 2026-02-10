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
AND it SHALL accept a `worker` parameter implementing the `Worker` protocol
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

### Requirement: Local Provider Protocol
The system SHALL define a `LocalProvider` protocol that encapsulates tool-specific configuration for local AI coding agents.

#### Scenario: LocalProvider Protocol Methods
- **WHEN** implementing the `LocalProvider` protocol
- **THEN** the implementation SHALL provide `build_command(task: str, error_context: str | None) -> str` to construct the shell command
- **AND** it SHALL provide `default_mode() -> Literal["interactive", "subprocess"]` to indicate the preferred execution mode
- **AND** it SHALL provide `detect() -> bool` to check if the tool is available on PATH
- **AND** it SHALL provide `name` and `description` string properties

#### Scenario: LocalProvider Structural Typing
- **WHEN** a class implements `build_command`, `default_mode`, `detect`, `name`, and `description` with correct signatures
- **THEN** it SHALL satisfy the `LocalProvider` protocol without explicit inheritance

### Requirement: Claude Code Provider
The system SHALL provide a `ClaudeCodeProvider` that configures the local runner for Anthropic's Claude Code CLI.

#### Scenario: Claude Code Subprocess Command
- **WHEN** `ClaudeCodeProvider.build_command(task, error_context)` is called
- **AND** the mode is `subprocess`
- **THEN** it SHALL return a command using `claude --print --output-format text -p "{task}"`
- **AND** if `error_context` is provided, it SHALL append `--append-system-prompt` with the verification feedback

#### Scenario: Claude Code Interactive Command
- **WHEN** `ClaudeCodeProvider.build_command(task, error_context)` is called
- **AND** the mode is `interactive`
- **THEN** it SHALL return `claude` for interactive TTY usage
- **AND** error context SHALL be delivered via the `VERIDICAL_ERROR_CONTEXT` environment variable

#### Scenario: Claude Code Detection
- **WHEN** `ClaudeCodeProvider.detect()` is called
- **THEN** it SHALL return `True` if `claude` is found on PATH
- **AND** it SHALL return `False` otherwise

### Requirement: Gemini CLI Provider
The system SHALL provide a `GeminiCliProvider` that configures the local runner for Google's Gemini CLI.

#### Scenario: Gemini CLI Subprocess Command
- **WHEN** `GeminiCliProvider.build_command(task, error_context)` is called
- **AND** the mode is `subprocess`
- **THEN** it SHALL return a command using `gemini -p "{task_with_error_context}"`
- **AND** if `error_context` is provided, it SHALL append the verification feedback to the prompt text

#### Scenario: Gemini CLI Interactive Command
- **WHEN** `GeminiCliProvider.build_command(task, error_context)` is called
- **AND** the mode is `interactive`
- **THEN** it SHALL return `gemini` for interactive TTY usage
- **AND** error context SHALL be delivered via the `VERIDICAL_ERROR_CONTEXT` environment variable

#### Scenario: Gemini CLI Detection
- **WHEN** `GeminiCliProvider.detect()` is called
- **THEN** it SHALL return `True` if `gemini` is found on PATH
- **AND** it SHALL return `False` otherwise

### Requirement: Provider-Aware Local Runner
The `LocalRunner` SHALL support receiving a `LocalProvider` to delegate command construction and error delivery.

#### Scenario: Runner with Provider
- **WHEN** `LocalRunner` is initialized with a `LocalProvider`
- **THEN** it SHALL use `provider.build_command()` to construct the command on each iteration
- **AND** it SHALL use the provider's error delivery strategy instead of the default env var approach

#### Scenario: Runner without Provider (Backward Compatibility)
- **WHEN** `LocalRunner` is initialized without a `LocalProvider`
- **THEN** it SHALL use `config.local.worker_command` as before
- **AND** it SHALL deliver error context via the `config.local.error_env_var` environment variable
- **AND** existing behavior SHALL be fully preserved

### Requirement: Worker Protocol Definition
The system SHALL define a `Worker` protocol that abstracts AI agent backends.

#### Scenario: Worker Protocol Methods
- **WHEN** implementing the `Worker` protocol
- **THEN** the implementation SHALL provide `dispatch(task: str, error_context: str | None) -> WorkResult`
- **AND** it SHALL provide `poll(handle: WorkHandle) -> PollResult`
- **AND** it SHALL provide `sync(handle: WorkHandle) -> SyncResult`

#### Scenario: WorkHandle Opaque Token
- **WHEN** `dispatch()` returns a `WorkResult`
- **THEN** it SHALL include a `handle: WorkHandle` that is passed to `poll()` and `sync()`
- **AND** the supervisor SHALL NOT inspect the handle's internal structure

#### Scenario: Worker Protocol Structural Typing
- **WHEN** a class implements `dispatch`, `poll`, and `sync` methods with correct signatures
- **THEN** it SHALL satisfy the `Worker` protocol without explicit inheritance

### Requirement: Jules Worker Implementation
The system SHALL provide a `JulesWorker` class that implements the `Worker` protocol using the existing Jules API integration.

#### Scenario: JulesWorker Dispatch
- **WHEN** `JulesWorker.dispatch(task, error_context)` is called
- **THEN** it SHALL create a Jules session via the existing `Dispatcher`
- **AND** return a `WorkResult` with the session ID as the handle

#### Scenario: JulesWorker Poll
- **WHEN** `JulesWorker.poll(handle)` is called
- **THEN** it SHALL poll the Jules session via the existing `Poller`
- **AND** return a `PollResult` with the session's terminal state

#### Scenario: JulesWorker Sync
- **WHEN** `JulesWorker.sync(handle)` is called
- **THEN** it SHALL download and apply the patch via the existing `Synchronizer`
- **AND** return a `SyncResult` with patch application status and diff hash

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

