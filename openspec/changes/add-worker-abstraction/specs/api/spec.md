## MODIFIED Requirements

### Requirement: Jules Client Interface

The system SHALL provide an async HTTP client for the Jules REST API. The client SHALL be used internally by `JulesWorker` rather than directly by the `Supervisor`.

#### Scenario: Client Initialization

WHEN instantiating `JulesClient`
THEN it SHALL accept `api_key: str` and `base_url: str` parameters
AND it SHALL configure HTTPX with appropriate timeouts

#### Scenario: Authentication Headers

WHEN making API requests
THEN it SHALL include `Authorization: Bearer {api_key}` header
AND it SHALL include `Content-Type: application/json` header
