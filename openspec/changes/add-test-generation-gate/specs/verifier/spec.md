## ADDED Requirements

### Requirement: Test Generation Gate Type
The system SHALL support a `test_generation` gate type that verifies new/changed code has corresponding test coverage.

#### Scenario: Uncovered New Function Detected
- **WHEN** a `test_generation` gate is configured
- **AND** the current diff introduces a new function `validate_password()` in `src/auth.py:42`
- **AND** no test covers that function
- **THEN** the gate SHALL fail
- **AND** the output SHALL list the uncovered function with its file:line reference

#### Scenario: All New Functions Covered
- **WHEN** a `test_generation` gate is configured
- **AND** the current diff introduces new functions
- **AND** all new functions have corresponding test coverage above the configured threshold
- **THEN** the gate SHALL pass

#### Scenario: Coverage Command Execution
- **WHEN** a `test_generation` gate runs
- **THEN** it SHALL execute the configured `coverage_command` (default: `pytest --cov --cov-report=json`)
- **AND** it SHALL parse the coverage output in the configured `coverage_format` (default: `pytest-cov-json`)

#### Scenario: Coverage Threshold Check
- **WHEN** a `test_generation` gate is configured with `coverage_threshold: 80`
- **AND** the new functions have 60% line coverage
- **THEN** the gate SHALL fail with a message indicating the coverage shortfall

#### Scenario: No New Functions in Diff
- **WHEN** a `test_generation` gate runs
- **AND** the current diff does not introduce any new functions (e.g., config-only changes)
- **THEN** the gate SHALL pass with a note that no new functions were detected

#### Scenario: Structured Feedback Output
- **WHEN** a `test_generation` gate fails
- **THEN** the feedback SHALL list each uncovered function in the format: `{file}:{line} - {function_name} (coverage: {percent}%)`
- **AND** the feedback SHALL be compatible with the existing `FeedbackGenerator` pipeline

### Requirement: Diff-Aware Coverage Analyzer
The system SHALL provide a `DiffCoverageAnalyzer` class that cross-references git diffs with coverage reports.

#### Scenario: Diff Parsing
- **WHEN** calling `analyzer.parse_diff(diff_text)`
- **THEN** it SHALL extract a list of new/changed function definitions with their file paths and line numbers

#### Scenario: Coverage Cross-Reference
- **WHEN** calling `analyzer.check_coverage(diff_functions, coverage_report)`
- **THEN** it SHALL return a list of `UncoveredFunction` objects for functions below the threshold
- **AND** each object SHALL contain `file_path`, `line_number`, `function_name`, and `coverage_percent`
