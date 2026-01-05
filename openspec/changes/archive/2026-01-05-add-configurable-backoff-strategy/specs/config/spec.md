# config Specification Delta

## MODIFIED Requirements

### Requirement: Configuration Schema

The system SHALL define a `VeridicalConfig` Pydantic model.

#### Scenario: Jules Config Section

WHEN accessing `config.jules`
THEN it SHALL contain `api_base_url: str` (default: `https://jules.googleapis.com/v1alpha`)
AND it SHALL contain `poll_interval: int` (default: 30)
AND it SHALL contain `poll_timeout: int` (default: 3600)
AND it SHALL contain `auto_approve_plans: bool` (default: True)
AND it SHALL contain `backoff_strategy: Literal["constant", "exponential"]` (default: `constant`)

> **Delta**: Added `backoff_strategy` field with `constant` as default.
