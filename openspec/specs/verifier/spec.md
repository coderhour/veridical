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

### Requirement: Feedback Compression
The `Verifier` SHALL produce concise feedback from verbose logs using either heuristic or semantic analysis.

#### Scenario: Generic Error Extraction (Default)
- **GIVEN** a verbose process output and no local LLM configured
- **WHEN** `generate_feedback` is called
- **THEN** it must extract the lines containing error keywords ("error", "failed")
- **AND** include surrounding context lines (N lines before/after)
- **AND** produce an output < `summary_max_length`

#### Scenario: Tail Retention (Fallback)
- **GIVEN** a failed process output with no detectable error keywords
- **WHEN** `generate_feedback` is called
- **THEN** it must return the last N lines of the output (tail summary)

#### Scenario: RLM-based Extraction (Configured)
- **GIVEN** a local LLM is configured AND `feedback_mode` is "rlm" or "auto"
- **AND** the log length exceeds the processing threshold (e.g. 1000 lines)
- **WHEN** `generate_feedback` is called
- **THEN** it SHALL use the configured LLM to recursively summarize the log chunks
- **AND** return a semantically condensed summary identifying the root cause

### Requirement: Task Completion Verification

The task_completion quality gate SHALL support dynamic path detection.

#### Scenario: Auto Path Configuration

WHEN a task_completion gate is configured with `path: auto`
THEN the verifier SHALL use the dynamically detected tasks.md path from the current spec context
AND if no spec is selected, it SHALL skip the task_completion gate

#### Scenario: Explicit Path Configuration

WHEN a task_completion gate is configured with an explicit path (e.g., `path: openspec/changes/foo/tasks.md`)
THEN the verifier SHALL use the explicitly configured path
AND the behavior SHALL remain unchanged from current implementation

#### Scenario: Default Configuration

WHEN the default VerifierConfig is used
THEN the task_completion gate SHALL default to `path: auto`
AND it SHALL integrate with the dynamic spec detection system

### Requirement: Local LLM Integration
The system SHALL support integration with a local OpenAI-compatible LLM endpoint.

#### Scenario: Configuration
- **WHEN** `local_llm.base_url` and `local_llm.model` are set in configuration
- **THEN** the system SHALL initialize an LLM client with these settings

#### Scenario: Log Analysis Request
- **WHEN** verification fails and RLM analysis is triggered
- **THEN** the system SHALL send log content to the local LLM
- **AND** request a summary of the failure

### Requirement: Parallel Quality Gate Execution
The system SHALL support executing quality gates in parallel when configured.

#### Scenario: Parallel Gates Run Concurrently
- **WHEN** multiple gates are configured with `parallel: true`
- **THEN** they SHALL execute concurrently using `asyncio.gather()`
- **AND** the total duration SHALL be approximately the longest gate duration

#### Scenario: Sequential Gates Run In Order
- **WHEN** gates are configured with `parallel: false` (default)
- **THEN** they SHALL execute sequentially in configuration order
- **AND** fail-fast behavior SHALL stop execution on first required failure

#### Scenario: Mixed Parallel and Sequential Execution
- **WHEN** some gates have `parallel: true` and others `parallel: false`
- **THEN** the system SHALL group consecutive parallel gates into batches
- **AND** execute each batch concurrently
- **AND** maintain sequential ordering between batches

#### Scenario: Parallel Fail-Fast Cancellation
- **WHEN** a required gate fails within a parallel batch
- **THEN** the system SHALL cancel remaining gates in that batch
- **AND** the system SHALL NOT start subsequent batches
- **AND** the failure result SHALL be returned immediately

#### Scenario: Parallel Gate Timeout
- **WHEN** a parallel batch exceeds `parallel_timeout` seconds
- **THEN** all gates in the batch SHALL be cancelled
- **AND** a timeout error SHALL be recorded for each cancelled gate

### Requirement: LLM-Powered Feedback Mode
The system SHALL use the configured local LLM to generate intelligent feedback summaries.

#### Scenario: RLM Mode Activation
- **WHEN** `feedback_mode` is "rlm" or "auto"
- **AND** local LLM is configured
- **AND** output exceeds `rlm_threshold` lines
- **THEN** the system SHALL use the LLM for summarization

#### Scenario: Recursive Chunk Summarization
- **WHEN** LLM summarization is triggered
- **AND** output exceeds `chunk_size` lines
- **THEN** the system SHALL split output into chunks
- **AND** summarize each chunk individually
- **AND** combine chunk summaries into final summary

#### Scenario: Structured Error Extraction
- **WHEN** LLM summarization completes
- **THEN** the output SHALL prioritize file:line:message format
- **AND** group related errors together
- **AND** identify root cause vs symptom errors

#### Scenario: LLM Fallback on Failure
- **WHEN** LLM request times out or fails
- **THEN** the system SHALL fall back to heuristic mode
- **AND** log a warning about the fallback
- **AND** return a valid feedback string

### Requirement: Feedback Mode Configuration
The system SHALL support configurable feedback generation modes.

#### Scenario: Heuristic Mode
- **WHEN** `feedback_mode` is "heuristic"
- **THEN** the system SHALL use keyword-based extraction only
- **AND** SHALL NOT invoke the local LLM

#### Scenario: Auto Mode Selection
- **WHEN** `feedback_mode` is "auto"
- **AND** local LLM is configured
- **THEN** the system SHALL use RLM for large outputs
- **AND** use heuristic for small outputs below threshold

#### Scenario: Missing LLM Configuration
- **WHEN** `feedback_mode` is "rlm"
- **AND** local LLM is NOT configured
- **THEN** the system SHALL log a warning
- **AND** fall back to heuristic mode

