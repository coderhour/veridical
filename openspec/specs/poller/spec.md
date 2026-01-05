# poller Specification

## Purpose
TBD - created by archiving change scaffold-foundation. Update Purpose after archive.
## Requirements
### Requirement: Poller Module Structure

The system SHALL provide a `veridical.poller` module for monitoring Jules session status.

#### Scenario: Module Import

WHEN importing `from veridical.poller import Poller`
THEN the import SHALL succeed without errors

#### Scenario: Poller Interface

WHEN instantiating the Poller class
THEN it SHALL accept a `config` parameter of type `VeridicalConfig`
AND it SHALL accept an `api_client` parameter of type `JulesClient`

### Requirement: Status Polling

The system SHALL poll Jules API for session status updates.

#### Scenario: Poll Until Complete

WHEN calling `await poller.wait_for_completion(session_id: str)`
THEN it SHALL poll the session status at configured intervals
AND it SHALL return when status is `COMPLETED` or `FAILED`
AND it SHALL return a `PollResult` containing `status`, `logs`, and `duration`

#### Scenario: Polling Timeout

WHEN polling exceeds the configured `poll_timeout` duration
THEN it SHALL raise `TimeoutError` with session context

### Requirement: Plan Approval Bypass

The system SHALL automatically approve plans when in autonomous mode.

#### Scenario: Waiting for Plan Approval

WHEN poll returns status `WAITING_FOR_PLAN_APPROVAL`
AND autonomous mode is enabled
THEN the Poller SHALL call the `:approvePlan` endpoint
AND it SHALL continue polling

#### Scenario: User Input Required

WHEN poll returns status `WAITING_FOR_INPUT`
THEN the Poller SHALL send a default continuation message
AND it SHALL log a warning about the agent requesting input

### Requirement: Configurable Backoff Strategy

The system SHALL support configurable backoff strategies for polling intervals.

> **Delta**: Renamed from "Exponential Backoff Strategy" to reflect configurability. The system now supports both constant and exponential strategies, with constant as the default.

#### Scenario: Constant Backoff (Default)

WHEN `config.jules.backoff_strategy` is `constant` (or unset)
THEN the polling interval SHALL remain fixed at `poll_interval` for every poll attempt

#### Scenario: Exponential Backoff

WHEN `config.jules.backoff_strategy` is `exponential`
THEN the first interval SHALL be `poll_interval` (default 30 seconds)
AND subsequent intervals SHALL be `min(previous * 2, max_interval)`
AND random jitter of +/- 10% SHALL be applied
AND the maximum interval SHALL be capped at 300 seconds

#### Scenario: Strategy Selection

WHEN initializing the Poller
THEN it SHALL read `config.jules.backoff_strategy`
AND it SHALL instantiate `ConstantBackoff` for `constant` strategy
AND it SHALL instantiate `ExponentialBackoff` for `exponential` strategy

### Requirement: Progress Reporting
The system SHALL provide real-time progress feedback during polling.

#### Scenario: Spinner Display
- **WHEN** polling is active
- **THEN** a spinner SHALL be displayed indicating activity
- **AND** the current session state SHALL be shown
- **AND** elapsed time SHALL be displayed

#### Scenario: Iteration Counter
- **WHEN** the supervisor is on iteration N of max M
- **THEN** the display SHALL show "Iteration N/M"
- **AND** the counter SHALL update on each new iteration

#### Scenario: Non-TTY Fallback
- **WHEN** output is not a TTY (e.g., CI/CD pipeline)
- **THEN** progress SHALL be logged as periodic status lines
- **AND** spinners SHALL NOT be used

### Requirement: Activity Streaming
The system SHALL support streaming Jules activity logs.

#### Scenario: Verbose Mode Enabled
- **WHEN** `--verbose` flag is passed to `veri run`
- **THEN** the system SHALL fetch activities on each poll
- **AND** new activities SHALL be displayed in real-time
- **AND** file operations SHALL be formatted for readability

#### Scenario: Activity Summary
- **WHEN** verbose mode is disabled
- **AND** activities contain file operations
- **THEN** a summary line SHALL show files being modified
- **AND** the summary SHALL update on state changes

#### Scenario: Activity Parsing
- **WHEN** parsing activity entries from Jules API
- **THEN** file read/write operations SHALL be extracted
- **AND** test execution results SHALL be highlighted
- **AND** errors SHALL be displayed prominently

### Requirement: Clean Interruption Handling
The system SHALL clean up progress display on interruption.

#### Scenario: SIGINT During Polling
- **WHEN** SIGINT is received during active polling
- **THEN** the progress spinner SHALL be hidden
- **AND** terminal state SHALL be restored
- **AND** a clean status line SHALL be printed

