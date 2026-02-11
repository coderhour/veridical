## ADDED Requirements

### Requirement: Intake Module Structure
The system SHALL provide a `veridical.intake` module for fetching, triaging, and converting external issue reports into supervisor-ready tasks.

#### Scenario: Module Import
- **WHEN** importing `from veridical.intake import IssueFetcher, TriageClassifier, TaskGenerator`
- **THEN** the import SHALL succeed without errors

### Requirement: Issue Fetcher
The system SHALL provide an `IssueFetcher` class that retrieves issue data from GitHub via the REST API.

#### Scenario: Fetch Single Issue
- **WHEN** calling `await fetcher.fetch(owner="org", repo="repo", issue_number=42)`
- **THEN** it SHALL return an `IssueData` model containing title, body, labels, author, and linked stack traces
- **AND** it SHALL use the `GITHUB_TOKEN` environment variable for authentication

#### Scenario: Issue Not Found
- **WHEN** calling `await fetcher.fetch()` with a non-existent issue number
- **THEN** it SHALL raise an `IntakeError` with a message indicating the issue was not found

#### Scenario: Rate Limit Handling
- **WHEN** the GitHub API returns a 429 or `X-RateLimit-Remaining: 0` response
- **THEN** it SHALL wait until the `X-RateLimit-Reset` time before retrying
- **AND** it SHALL log a warning about rate limiting

#### Scenario: Missing GitHub Token
- **WHEN** `GITHUB_TOKEN` is not set in the environment
- **THEN** it SHALL raise a `ConfigurationError` with instructions to set the token

### Requirement: Triage Classifier
The system SHALL provide a `TriageClassifier` that categorizes issues and estimates complexity.

#### Scenario: Bug Classification
- **WHEN** calling `classifier.classify(issue_data)` with an issue containing labels `["bug"]` or body containing stack traces
- **THEN** it SHALL return a `TriageResult` with `category="bug"` and an estimated `complexity` of `"low"`, `"medium"`, or `"high"`

#### Scenario: Feature Classification
- **WHEN** calling `classifier.classify(issue_data)` with an issue containing labels `["enhancement", "feature"]`
- **THEN** it SHALL return a `TriageResult` with `category="feature"`

#### Scenario: Complexity Estimation
- **WHEN** classifying an issue
- **THEN** complexity SHALL be estimated based on: number of files referenced, presence of stack traces, issue body length, and label hints
- **AND** `complexity` SHALL be one of `"low"`, `"medium"`, `"high"`

### Requirement: Task Generator
The system SHALL provide a `TaskGenerator` that converts issue data and triage results into a task description string compatible with `Supervisor.run()`.

#### Scenario: Bug Task Generation
- **WHEN** calling `generator.generate(issue_data, triage_result)` for a bug
- **THEN** it SHALL return a task description string containing the issue title, reproduction steps (if present), stack trace excerpts, and affected file hints
- **AND** the output SHALL be a plain string suitable for `Supervisor.run(task_description=...)`

#### Scenario: Feature Task Generation
- **WHEN** calling `generator.generate(issue_data, triage_result)` for a feature
- **THEN** it SHALL return a task description string containing the feature requirements extracted from the issue body

#### Scenario: Task Length Limit
- **WHEN** generating a task description
- **THEN** the output SHALL NOT exceed 4000 characters
- **AND** it SHALL prioritize stack traces and error messages over general description text

### Requirement: PR Publisher
The system SHALL provide a `PRPublisher` class that creates GitHub pull requests with verification evidence.

#### Scenario: Create PR on Success
- **WHEN** calling `await publisher.publish(issue_data, loop_result, branch_name)`
- **AND** `loop_result.success` is `True`
- **THEN** it SHALL create a GitHub PR targeting the repository's default branch
- **AND** the PR title SHALL reference the issue number (e.g., "Fix #42: <issue title>")
- **AND** the PR body SHALL contain: issue link, root-cause summary, iteration count, and quality gate results

#### Scenario: Comment on Failure
- **WHEN** calling `await publisher.publish(issue_data, loop_result, branch_name)`
- **AND** `loop_result.success` is `False`
- **THEN** it SHALL post a comment on the GitHub issue with a diagnostic summary
- **AND** the comment SHALL include the failure reason and last error context

#### Scenario: Dry Run Mode
- **WHEN** `publisher` is initialized with `dry_run=True`
- **THEN** it SHALL log what it would do without making any GitHub API calls
