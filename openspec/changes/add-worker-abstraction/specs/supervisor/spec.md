## MODIFIED Requirements

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

## ADDED Requirements

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
