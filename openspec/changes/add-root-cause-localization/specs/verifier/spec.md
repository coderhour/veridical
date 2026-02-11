## ADDED Requirements

### Requirement: Localization-Enriched Feedback
The `FeedbackGenerator` SHALL support enriching error feedback with root-cause localization data when a `Localizer` is available.

#### Scenario: Enriched Feedback with Localizer
- **WHEN** `generate_feedback(result, localizer)` is called with a `Localizer` instance
- **AND** the verification result contains failures with stack traces
- **THEN** the feedback SHALL include localization data prepended to the gate failure summary
- **AND** the localization section SHALL list ranked candidate locations in the format: "Root cause likely in {file}:{line} ({function}) - confidence: {score}"

#### Scenario: Feedback Without Localizer (Backward Compatible)
- **WHEN** `generate_feedback(result)` is called without a `Localizer` instance
- **THEN** the behavior SHALL be identical to the current implementation
- **AND** no localization analysis SHALL be performed

#### Scenario: Localization Failure Fallback
- **WHEN** localization analysis fails (e.g., AST parse error, git blame error)
- **THEN** the feedback SHALL fall back to the existing heuristic/RLM output
- **AND** a warning SHALL be logged about the localization failure
