# verifier Specification

## Purpose
TBD - created by archiving change scaffold-foundation. Update Purpose after archive.
## Requirements
### Requirement: Verifier Module Structure

The system SHALL provide a `veridical.verifier` module for running local quality gates.

#### Scenario: Module Import

WHEN importing `from veridical.verifier import Verifier`
THEN the import SHALL succeed without errors

#### Scenario: Verifier Interface

WHEN instantiating the Verifier class
THEN it SHALL accept a `config` parameter of type `VeridicalConfig`
AND it SHALL accept a `repo_path` parameter of type `Path`

### Requirement: Quality Gate Execution

The system SHALL execute configured quality gate commands (tests, linters).

#### Scenario: Run All Gates

WHEN calling `await verifier.run_all()`
THEN it SHALL execute each configured command in sequence
AND it SHALL return a `VerificationResult` with overall pass/fail

#### Scenario: Individual Gate Execution

WHEN calling `await verifier.run_gate(gate_name: str)`
THEN it SHALL execute only the specified gate
AND it SHALL return the result for that gate

### Requirement: Command Configuration

The system SHALL read quality gate commands from configuration.

#### Scenario: Default Gates

WHEN no custom gates are configured
THEN the Verifier SHALL use default gates: `pytest`, `ruff check src/`, `mypy src/`

#### Scenario: Custom Gates

WHEN `.veridical.yaml` contains a `quality_gates` section
THEN the Verifier SHALL use those commands instead of defaults

### Requirement: Output Capture

The system SHALL capture stdout and stderr from quality gate commands.

#### Scenario: Successful Gate

WHEN a gate command exits with code 0
THEN `GateResult.passed` SHALL be `True`
AND `GateResult.output` SHALL contain stdout

#### Scenario: Failed Gate

WHEN a gate command exits with non-zero code
THEN `GateResult.passed` SHALL be `False`
AND `GateResult.output` SHALL contain stdout
AND `GateResult.error_output` SHALL contain stderr

### Requirement: Feedback Generation

The system SHALL summarize verification failures for feedback to the next iteration.

#### Scenario: Generate Error Summary

WHEN calling `verifier.generate_feedback(result: VerificationResult)`
AND the result contains failures
THEN it SHALL return a summarized error context
AND the summary SHALL be limited to the most relevant 2000 characters
AND the summary SHALL prioritize stack traces and error messages

#### Scenario: No Failures

WHEN calling `verifier.generate_feedback(result: VerificationResult)`
AND all gates passed
THEN it SHALL return an empty string

### Requirement: Verification Result Model

The system SHALL define a `VerificationResult` model.

#### Scenario: Result Structure

WHEN a verification completes
THEN `VerificationResult.passed` SHALL be `True` if all gates passed
AND `VerificationResult.gates` SHALL contain a list of `GateResult` objects
AND `VerificationResult.duration` SHALL contain total execution time

