## ADDED Requirements

### Requirement: Jules Supervisor E2E Test Coverage
The system SHALL have end-to-end tests that exercise the full Jules-based supervisor loop against mock workers in temporary git repositories.

#### Scenario: Happy Path Full Loop
- **GIVEN** a mock worker that produces a patch passing all quality gates
- **WHEN** the supervisor loop runs
- **THEN** it SHALL complete with SUCCESS on the first iteration
- **AND** the final commit SHALL exist on the work branch

#### Scenario: Retry After Verification Failure
- **GIVEN** a mock worker that produces a failing patch on iteration 1 and a passing patch on iteration 2
- **WHEN** the supervisor loop runs
- **THEN** it SHALL complete with SUCCESS after 2 iterations
- **AND** error context from iteration 1 SHALL be passed to the worker for iteration 2

#### Scenario: Circuit Breaker Trip
- **GIVEN** a mock worker that always produces failing patches
- **WHEN** the supervisor loop runs with `max_iterations: 3`
- **THEN** it SHALL terminate with FAILED after exceeding max iterations
- **AND** the failure reason SHALL indicate "Maximum iterations exceeded"

#### Scenario: Stagnation Detection
- **GIVEN** a mock worker that produces identical patches on every iteration
- **WHEN** the supervisor loop runs with `stagnation_threshold: 2`
- **THEN** it SHALL terminate with FAILED
- **AND** the failure reason SHALL indicate stagnation

#### Scenario: Branch State Correctness
- **WHEN** the supervisor loop runs through multiple iterations
- **THEN** verification SHALL execute on the iteration branch
- **AND** the repository SHALL return to the main branch after completion

#### Scenario: Resume Existing Session
- **GIVEN** a valid session ID is provided
- **WHEN** the supervisor loop runs with that session ID
- **THEN** it SHALL skip session creation and poll the existing session directly

### Requirement: Local Supervisor E2E Test Coverage
The system SHALL have end-to-end tests that exercise the `LocalSupervisor` loop with mock worker commands.

#### Scenario: Local Loop Success After Retry
- **GIVEN** a worker script that produces incorrect output on the first run and correct output after receiving error context
- **WHEN** the local supervisor loop runs via `veri local`
- **THEN** it SHALL complete with SUCCESS after 2 iterations
- **AND** the final file content SHALL match the expected output

#### Scenario: Local Loop Circuit Breaker
- **GIVEN** a worker script that always produces failing output
- **WHEN** the local supervisor loop runs with `max_iterations: 3`
- **THEN** it SHALL terminate with FAILED after exceeding max iterations

#### Scenario: Local Loop With Provider
- **GIVEN** a named local provider (e.g., `claude-code`)
- **WHEN** the local supervisor loop runs with `--provider`
- **THEN** it SHALL use the provider's `build_command()` to construct the worker command

### Requirement: State Persistence E2E Test Coverage
The system SHALL have tests that verify state persistence and resume behavior.

#### Scenario: State Restoration
- **GIVEN** a `.veridical_state.json` file from a previous interrupted run
- **WHEN** the supervisor resumes with `resume_from_state=True`
- **THEN** it SHALL restore the session ID and iteration count
- **AND** continue from the saved state

#### Scenario: State Cleanup On Success
- **WHEN** the supervisor loop completes successfully
- **THEN** the `.veridical_state.json` file SHALL be deleted

### Requirement: Integration Test Coverage for Component Interactions
The system SHALL have integration tests that verify interactions between major components.

#### Scenario: Report Generation Round-Trip
- **GIVEN** work log entries written by `WorkLogWriter`
- **WHEN** `ReportGenerator` reads the worklog directory
- **THEN** it SHALL produce correct `RunSummary` objects
- **AND** `TerminalFormatter`, `JsonFormatter`, and `HtmlFormatter` SHALL render valid output

#### Scenario: LLM Feedback Integration
- **GIVEN** a verification result with failed gates and large log output
- **WHEN** `FeedbackGenerator` processes the result with an LLM client
- **THEN** it SHALL produce a summarized error context suitable for the next iteration

#### Scenario: Log Analyzer Chunking
- **GIVEN** a log output exceeding the configured `chunk_size`
- **WHEN** `LogAnalyzer.analyze_log()` is called
- **THEN** it SHALL split the log into chunks and call the LLM for each chunk
- **AND** it SHALL build a recursive summary across chunks

#### Scenario: Local Provider CLI Integration
- **WHEN** `veri local --list-providers` is invoked
- **THEN** it SHALL display all registered providers with detection status
- **AND** `--provider claude-code --dry-run` SHALL resolve the provider without error

#### Scenario: gtr CLI Integration
- **GIVEN** gtr is detected on PATH
- **WHEN** `veri local --gtr --dry-run` is invoked
- **THEN** it SHALL generate a `veri/` prefixed branch name
- **AND** display the worktree branch in output

#### Scenario: WorkLog Round-Trip
- **GIVEN** multiple `WorkLogEntry` objects written via `WorkLogWriter`
- **WHEN** the JSONL file is read back
- **THEN** all entries SHALL be present with correct fields

### Requirement: Test Infrastructure
The system SHALL provide reusable test fixtures and markers for E2E and integration testing.

#### Scenario: Mock Worker Fixture
- **WHEN** tests require a mock AI worker
- **THEN** a `MockJulesClient` fixture SHALL be available
- **AND** it SHALL support configuring deterministic patch responses per iteration

#### Scenario: Temporary Git Repository Fixture
- **WHEN** tests require git operations
- **THEN** a temporary git repository fixture SHALL be available
- **AND** it SHALL be initialized with a baseline commit and configured remote

#### Scenario: Pytest Markers
- **WHEN** running the test suite
- **THEN** `@pytest.mark.e2e`, `@pytest.mark.integration`, and `@pytest.mark.slow` markers SHALL be available
- **AND** `--strict-markers` SHALL be enabled in pytest configuration
