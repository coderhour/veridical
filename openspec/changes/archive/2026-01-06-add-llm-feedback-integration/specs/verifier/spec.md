## ADDED Requirements

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
