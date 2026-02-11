## ADDED Requirements

### Requirement: Diagnose Module Structure
The system SHALL provide a `veridical.diagnose` module for multi-signal root-cause localization of code failures.

#### Scenario: Module Import
- **WHEN** importing `from veridical.diagnose import Localizer, StackTraceParser, BlameCorrelator`
- **THEN** the import SHALL succeed without errors

### Requirement: Stack Trace Parser
The system SHALL provide a `StackTraceParser` class that extracts file:line references from error output.

#### Scenario: Python Traceback Parsing
- **WHEN** calling `parser.parse(traceback_text)` with a standard Python traceback
- **THEN** it SHALL return a list of `FrameReference` objects containing `file_path`, `line_number`, `function_name`, and `code_snippet`
- **AND** frames SHALL be ordered from innermost (crash site) to outermost (entry point)

#### Scenario: Generic Error Parsing
- **WHEN** calling `parser.parse(error_text)` with non-Python error output containing `file:line` patterns
- **THEN** it SHALL extract file:line references using common patterns (e.g., `filename.ext:42`, `at filename.ext line 42`)

#### Scenario: No Stack Trace Found
- **WHEN** calling `parser.parse(text)` with text containing no recognizable stack trace patterns
- **THEN** it SHALL return an empty list

### Requirement: Call Graph Analyzer
The system SHALL provide a `CallGraphAnalyzer` class that traces function call relationships using AST analysis.

#### Scenario: Trace Callers
- **WHEN** calling `analyzer.find_callers(file_path, function_name, repo_path)`
- **THEN** it SHALL parse Python source files using the `ast` module
- **AND** it SHALL return a list of call sites (file:line) that invoke the target function

#### Scenario: AST Parse Failure
- **WHEN** a source file contains syntax errors preventing AST parsing
- **THEN** the analyzer SHALL skip that file with a warning
- **AND** it SHALL continue analyzing remaining files

### Requirement: Blame Correlator
The system SHALL provide a `BlameCorrelator` class that identifies recent changes to crash-site code via `git blame`.

#### Scenario: Recent Change Detection
- **WHEN** calling `correlator.correlate(file_path, line_range, repo_path)`
- **THEN** it SHALL run `git blame` on the specified file and line range
- **AND** it SHALL return a list of `BlameEntry` objects with `commit_hash`, `author`, `date`, and `age_days`
- **AND** entries SHALL be sorted by recency (most recent first)

#### Scenario: Recency Scoring
- **WHEN** a blamed line was modified within the last 7 days
- **THEN** it SHALL receive a higher relevance score than older changes
- **AND** the score SHALL decrease logarithmically with age

### Requirement: Localizer Orchestrator
The system SHALL provide a `Localizer` class that orchestrates all localization signals into a ranked report.

#### Scenario: Multi-Signal Localization
- **WHEN** calling `localizer.localize(error_text, repo_path)`
- **THEN** it SHALL run `StackTraceParser`, `CallGraphAnalyzer`, and `BlameCorrelator` in sequence
- **AND** it SHALL produce a `LocalizationReport` ranking candidate root-cause locations by confidence score

#### Scenario: Localization Report Structure
- **WHEN** a `LocalizationReport` is generated
- **THEN** it SHALL contain a ranked list of `CandidateLocation` objects
- **AND** each candidate SHALL include `file_path`, `line_number`, `function_name`, `confidence_score` (0.0-1.0), and `evidence` (list of reasons)

#### Scenario: Localization Report Formatting
- **WHEN** calling `report.format()` on a `LocalizationReport`
- **THEN** it SHALL return a human-readable string in the format: "Root cause likely in {file}:{line} ({function}) - confidence: {score} - evidence: {reasons}"
- **AND** candidates SHALL be listed in descending confidence order

#### Scenario: Empty Localization
- **WHEN** localization finds no candidates (no stack traces, no blame data)
- **THEN** it SHALL return an empty `LocalizationReport`
- **AND** the formatted output SHALL indicate "No localization candidates found"
