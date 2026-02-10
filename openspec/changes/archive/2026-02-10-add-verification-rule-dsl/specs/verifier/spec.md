## ADDED Requirements

### Requirement: Assertion Gate Type
The system SHALL support an `assertion` gate type for declarative file and content checks.

#### Scenario: File Existence Assertion
- **WHEN** an assertion gate is configured with `assert_file_exists: ["src/main.py", "tests/*.py"]`
- **THEN** the gate SHALL pass if all matching files exist
- **AND** it SHALL fail with a list of missing files if any do not exist

#### Scenario: Content Pattern Assertion
- **WHEN** an assertion gate is configured with `assert_content_matches: {file: "README.md", pattern: "## Installation"}`
- **THEN** the gate SHALL pass if the file contains content matching the regex pattern
- **AND** it SHALL fail with the file path and expected pattern if no match is found

#### Scenario: JSON Schema Assertion
- **WHEN** an assertion gate is configured with `assert_json_schema: {file: "config.json", schema: "schemas/config.schema.json"}`
- **THEN** the gate SHALL validate the file against the JSON schema
- **AND** it SHALL fail with validation errors if the file does not conform

### Requirement: Diff Scope Gate Type
The system SHALL support a `diff_scope` gate type that verifies modified files against allowed patterns.

#### Scenario: Allowed File Patterns
- **WHEN** a diff_scope gate is configured with `allowed_patterns: ["src/**", "tests/**"]`
- **THEN** the gate SHALL pass if all modified files match at least one allowed pattern
- **AND** it SHALL fail listing files that were modified outside the allowed scope

#### Scenario: No Changes Detected
- **WHEN** a diff_scope gate runs and no files were modified
- **THEN** the gate SHALL pass

### Requirement: Conditional Gate Execution
The system SHALL support conditionally executing gates based on which files were modified.

#### Scenario: Gate Runs When Files Match
- **WHEN** a gate is configured with `when_files_changed: ["src/**/*.py"]`
- **AND** Python files in `src/` were modified in the current iteration
- **THEN** the gate SHALL execute normally

#### Scenario: Gate Skipped When No Files Match
- **WHEN** a gate is configured with `when_files_changed: ["src/**/*.py"]`
- **AND** no Python files in `src/` were modified
- **THEN** the gate SHALL be skipped
- **AND** the result SHALL indicate the gate was skipped with reason

### Requirement: Composite Gate Type
The system SHALL support a `composite` gate type that groups sub-gates with logical operators.

#### Scenario: All-Of Composite
- **WHEN** a composite gate is configured with `mode: all_of` and a list of sub-gates
- **THEN** the gate SHALL pass only if all sub-gates pass
- **AND** it SHALL fail if any sub-gate fails

#### Scenario: Any-Of Composite
- **WHEN** a composite gate is configured with `mode: any_of` and a list of sub-gates
- **THEN** the gate SHALL pass if at least one sub-gate passes
- **AND** it SHALL fail only if all sub-gates fail

#### Scenario: Nested Composite
- **WHEN** a composite gate contains another composite gate as a sub-gate
- **THEN** the system SHALL evaluate the nested composite recursively

### Requirement: Warning-Level Gate Results
The system SHALL support gates that produce warnings instead of failures.

#### Scenario: Warn-Only Gate
- **WHEN** a gate is configured with `warn_only: true`
- **AND** the gate fails
- **THEN** the result severity SHALL be `warn` instead of `fail`
- **AND** the verification loop SHALL NOT retry based on this gate

#### Scenario: Exit Code Mapping
- **WHEN** a command gate is configured with `exit_code_map: {0: pass, 1: fail, 2: warn}`
- **AND** the command exits with code 2
- **THEN** the result severity SHALL be `warn`
- **AND** the gate SHALL NOT block the loop

#### Scenario: Gate Result Severity Model
- **WHEN** a gate completes execution
- **THEN** the `GateResult` SHALL include a `severity` field with value `pass`, `warn`, or `fail`
- **AND** only `fail` severity SHALL cause the verification to fail overall
