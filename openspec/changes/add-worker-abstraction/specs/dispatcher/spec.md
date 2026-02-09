## MODIFIED Requirements

### Requirement: Dispatcher Module Structure

The system SHALL provide a `veridical.dispatcher` module for prompt construction and session management. The `Dispatcher` SHALL be used internally by `JulesWorker` rather than directly by the `Supervisor`.

#### Scenario: Module Import

WHEN importing `from veridical.dispatcher import Dispatcher`
THEN the import SHALL succeed without errors

#### Scenario: Dispatcher Interface

WHEN instantiating the Dispatcher class
THEN it SHALL accept a `config` parameter of type `VeridicalConfig`
AND it SHALL accept an `api_client` parameter of type `JulesClient`
