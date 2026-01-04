# Verifier Specification

## ADDED Requirements

### Requirement: Feedback Compression
The `Verifier` SHALL produce concise feedback from verbose logs.

#### Scenario: Generic Error Extraction
- **GIVEN** a verbose process output (> 500 lines) containing error keywords ("error", "failed")
- **WHEN** `generate_feedback` is called
- **THEN** it must extract the lines containing those keywords
- **AND** include surrounding context lines (N lines before/after)
- **AND** produce an output < `summary_max_length`

#### Scenario: Tail Retention
- **GIVEN** a failed process output with no detectable error keywords
- **WHEN** `generate_feedback` is called
- **THEN** it must return the last N lines of the output (tail summary)
