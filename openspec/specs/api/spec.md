# api Specification

## Purpose
TBD - created by archiving change scaffold-foundation. Update Purpose after archive.
## Requirements
### Requirement: API Module Structure

The system SHALL provide a `veridical.api` module for Jules API communication.

#### Scenario: Module Import

WHEN importing `from veridical.api import JulesClient`
THEN the import SHALL succeed without errors

### Requirement: Jules Client Interface

The system SHALL provide an async HTTP client for the Jules REST API.

#### Scenario: Client Initialization

WHEN instantiating `JulesClient`
THEN it SHALL accept `api_key: str` and `base_url: str` parameters
AND it SHALL configure HTTPX with appropriate timeouts

#### Scenario: Authentication Headers

WHEN making API requests
THEN it SHALL include `Authorization: Bearer {api_key}` header
AND it SHALL include `Content-Type: application/json` header

### Requirement: Session Management Endpoints

The system SHALL implement methods for Jules session lifecycle.

#### Scenario: Create Session

WHEN calling `await client.create_session(request: CreateSessionRequest)`
THEN it SHALL POST to `/v1alpha/sessions`
AND it SHALL return `SessionResponse` on success

#### Scenario: Get Session Status

WHEN calling `await client.get_session(session_id: str)`
THEN it SHALL GET from `/v1alpha/sessions/{session_id}`
AND it SHALL return `SessionResponse` with current status

#### Scenario: Approve Plan

WHEN calling `await client.approve_plan(session_id: str)`
THEN it SHALL POST to `/v1alpha/sessions/{session_id}:approvePlan`
AND it SHALL return success confirmation

#### Scenario: Send Message

WHEN calling `await client.send_message(session_id: str, message: str)`
THEN it SHALL POST to `/v1alpha/sessions/{session_id}:sendMessage`
AND it SHALL include the message in the request body

#### Scenario: Get Activities

WHEN calling `await client.get_activities(session_id: str)`
THEN it SHALL GET from `/v1alpha/sessions/{session_id}/activities`
AND it SHALL return a list of activity log entries

### Requirement: API Request/Response Models

The system SHALL define Pydantic models for API payloads.

#### Scenario: CreateSessionRequest Model

WHEN creating a session request
THEN `CreateSessionRequest` SHALL contain:
- `prompt: str`
- `source_context: SourceContext`
- `automation_mode: AutomationMode`
- `require_plan_approval: bool`

#### Scenario: SourceContext Model

WHEN specifying source context
THEN `SourceContext` SHALL contain:
- `source: str` (e.g., `sources/github/owner/repo`)
- `github_repo_context: GitHubRepoContext`

#### Scenario: SessionResponse Model

WHEN receiving a session response
THEN `SessionResponse` SHALL contain:
- `name: str` (session ID)
- `state: SessionState`
- `create_time: datetime`
- `update_time: datetime`

#### Scenario: SessionState Enum

WHEN parsing session state
THEN `SessionState` SHALL support values:
- `PENDING`
- `RUNNING`
- `WAITING_FOR_PLAN_APPROVAL`
- `WAITING_FOR_INPUT`
- `COMPLETED`
- `FAILED`

### Requirement: Error Handling

The system SHALL handle API errors gracefully.

#### Scenario: HTTP Error Response

WHEN the API returns a 4xx or 5xx status code
THEN it SHALL raise `APIError` with status code and message

#### Scenario: Network Timeout

WHEN a request times out
THEN it SHALL raise `APIError` with timeout information

#### Scenario: Rate Limiting

WHEN the API returns 429 Too Many Requests
THEN it SHALL raise `RateLimitError` with retry-after duration

### Requirement: Request Retries

The system SHALL implement retry logic for transient failures.

#### Scenario: Retry Configuration

WHEN initializing the client
THEN it SHALL accept `max_retries: int` (default: 3)
AND it SHALL accept `retry_delay: float` (default: 1.0)

#### Scenario: Retryable Errors

WHEN encountering a 5xx error or network issue
THEN it SHALL retry up to `max_retries` times
AND it SHALL use exponential backoff between retries

#### Scenario: Non-Retryable Errors

WHEN encountering a 4xx error (except 429)
THEN it SHALL NOT retry
AND it SHALL raise `APIError` immediately

