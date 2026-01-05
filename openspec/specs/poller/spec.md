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

