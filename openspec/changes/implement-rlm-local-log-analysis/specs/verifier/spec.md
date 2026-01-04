## MODIFIED Requirements
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

## ADDED Requirements
### Requirement: Local LLM Integration
The system SHALL support integration with a local OpenAI-compatible LLM endpoint.

#### Scenario: Configuration
- **WHEN** `local_llm.base_url` and `local_llm.model` are set in configuration
- **THEN** the system SHALL initialize an LLM client with these settings

#### Scenario: Log Analysis Request
- **WHEN** verification fails and RLM analysis is triggered
- **THEN** the system SHALL send log content to the local LLM
- **AND** request a summary of the failure
