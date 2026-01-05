## ADDED Requirements

### Requirement: Parallel Quality Gate Execution
The system SHALL support executing quality gates in parallel when configured.

#### Scenario: Parallel Gates Run Concurrently
- **WHEN** multiple gates are configured with `parallel: true`
- **THEN** they SHALL execute concurrently using `asyncio.gather()`
- **AND** the total duration SHALL be approximately the longest gate duration

#### Scenario: Sequential Gates Run In Order
- **WHEN** gates are configured with `parallel: false` (default)
- **THEN** they SHALL execute sequentially in configuration order
- **AND** fail-fast behavior SHALL stop execution on first required failure

#### Scenario: Mixed Parallel and Sequential Execution
- **WHEN** some gates have `parallel: true` and others `parallel: false`
- **THEN** the system SHALL group consecutive parallel gates into batches
- **AND** execute each batch concurrently
- **AND** maintain sequential ordering between batches

#### Scenario: Parallel Fail-Fast Cancellation
- **WHEN** a required gate fails within a parallel batch
- **THEN** the system SHALL cancel remaining gates in that batch
- **AND** the system SHALL NOT start subsequent batches
- **AND** the failure result SHALL be returned immediately

#### Scenario: Parallel Gate Timeout
- **WHEN** a parallel batch exceeds `parallel_timeout` seconds
- **THEN** all gates in the batch SHALL be cancelled
- **AND** a timeout error SHALL be recorded for each cancelled gate
