# dispatcher Specification

## Purpose
TBD - created by archiving change scaffold-foundation. Update Purpose after archive.
## Requirements
### Requirement: Dispatcher Module Structure

The system SHALL provide a `veridical.dispatcher` module for prompt construction and session management.

#### Scenario: Module Import

WHEN importing `from veridical.dispatcher import Dispatcher`
THEN the import SHALL succeed without errors

#### Scenario: Dispatcher Interface

WHEN instantiating the Dispatcher class
THEN it SHALL accept a `config` parameter of type `VeridicalConfig`
AND it SHALL accept an `api_client` parameter of type `JulesClient`

### Requirement: Sandwich Prompt Construction

The system SHALL construct prompts using a three-layer "sandwich" structure.

#### Scenario: Prompt Assembly

WHEN calling `dispatcher.build_prompt(task: str, error_context: str | None)`
THEN the result SHALL contain a role definition layer at the top
AND it SHALL contain the user task in the middle
AND it SHALL contain constraint injection at the bottom

#### Scenario: Error Context Injection

WHEN `error_context` is provided to `build_prompt`
THEN the constraint layer SHALL include the error details
AND the constraint layer SHALL instruct the agent to address the specific errors

### Requirement: Session Creation Interface

The system SHALL provide methods to create Jules sessions via the API.

#### Scenario: Create Session

WHEN calling `await dispatcher.create_session(prompt: str, branch: str)`
THEN it SHALL call the Jules API with `requirePlanApproval=False`
AND it SHALL return a `SessionInfo` object containing `session_id` and `status`

#### Scenario: Session Creation Failure

WHEN the Jules API returns an error during session creation
THEN it SHALL raise `APIError` with the error details

### Requirement: AGENTS.md Dynamic Injection

The system SHALL support dynamically modifying AGENTS.md content for each iteration.

#### Scenario: Ephemeral Constraint Injection

WHEN calling `dispatcher.inject_constraints(constraints: list[str])`
THEN it SHALL append an `# EPHEMERAL CONSTRAINT` section to the AGENTS.md content
AND these constraints SHALL be included in the prompt context

