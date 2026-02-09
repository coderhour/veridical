## ADDED Requirements

### Requirement: Report Subcommand
The CLI SHALL provide a `report` subcommand to generate structured summaries of completed runs.

#### Scenario: Report for Latest Run
- **WHEN** running `veri report`
- **THEN** it SHALL display a summary of the most recent run from the work log directory
- **AND** the summary SHALL include iteration count, total duration, and final outcome

#### Scenario: Report with Date Filter
- **WHEN** running `veri report --date 2026-02-09`
- **THEN** it SHALL display summaries for all runs on the specified date
- **AND** it SHALL list runs chronologically if multiple exist

#### Scenario: Report Format Selection
- **WHEN** running `veri report --format json`
- **THEN** it SHALL output the report in JSON format
- **AND** supported formats SHALL be `terminal`, `json`, and `html`

#### Scenario: Report Output to File
- **WHEN** running `veri report --format html --output report.html`
- **THEN** it SHALL write the report to the specified file
- **AND** it SHALL confirm the file path on success

#### Scenario: Report List Available Runs
- **WHEN** running `veri report --list`
- **THEN** it SHALL display a table of all available runs with date, task description, outcome, and iteration count

#### Scenario: No Runs Available
- **WHEN** running `veri report`
- **AND** no work log files exist
- **THEN** it SHALL display "No runs found. Run `veri run` first to generate work logs."
- **AND** it SHALL exit with code 1

### Requirement: Report Content
The report SHALL include per-iteration breakdown and aggregate metrics.

#### Scenario: Per-Iteration Breakdown
- **WHEN** a report is generated
- **THEN** each iteration SHALL show: iteration number, duration, gates executed, gates failed, feedback excerpt (truncated to 200 chars)

#### Scenario: Aggregate Metrics
- **WHEN** a report is generated
- **THEN** it SHALL include: total duration, total iterations, success/failure outcome, most-failed gate name, and cost estimate (if available)

#### Scenario: Pattern Insights
- **WHEN** a report is generated for a run with 3+ iterations
- **THEN** it SHALL include pattern insights such as "Gate 'pytest' failed on 3/5 iterations" or "Stagnation detected: same error on iterations 2-4"
