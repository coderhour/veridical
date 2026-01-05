# poller Specification Delta

## MODIFIED Requirements

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
