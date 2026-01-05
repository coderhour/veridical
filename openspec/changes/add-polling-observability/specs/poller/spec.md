## ADDED Requirements

### Requirement: Progress Reporting
The system SHALL provide real-time progress feedback during polling.

#### Scenario: Spinner Display
- **WHEN** polling is active
- **THEN** a spinner SHALL be displayed indicating activity
- **AND** the current session state SHALL be shown
- **AND** elapsed time SHALL be displayed

#### Scenario: Iteration Counter
- **WHEN** the supervisor is on iteration N of max M
- **THEN** the display SHALL show "Iteration N/M"
- **AND** the counter SHALL update on each new iteration

#### Scenario: Non-TTY Fallback
- **WHEN** output is not a TTY (e.g., CI/CD pipeline)
- **THEN** progress SHALL be logged as periodic status lines
- **AND** spinners SHALL NOT be used

### Requirement: Activity Streaming
The system SHALL support streaming Jules activity logs.

#### Scenario: Verbose Mode Enabled
- **WHEN** `--verbose` flag is passed to `veri run`
- **THEN** the system SHALL fetch activities on each poll
- **AND** new activities SHALL be displayed in real-time
- **AND** file operations SHALL be formatted for readability

#### Scenario: Activity Summary
- **WHEN** verbose mode is disabled
- **AND** activities contain file operations
- **THEN** a summary line SHALL show files being modified
- **AND** the summary SHALL update on state changes

#### Scenario: Activity Parsing
- **WHEN** parsing activity entries from Jules API
- **THEN** file read/write operations SHALL be extracted
- **AND** test execution results SHALL be highlighted
- **AND** errors SHALL be displayed prominently

### Requirement: Clean Interruption Handling
The system SHALL clean up progress display on interruption.

#### Scenario: SIGINT During Polling
- **WHEN** SIGINT is received during active polling
- **THEN** the progress spinner SHALL be hidden
- **AND** terminal state SHALL be restored
- **AND** a clean status line SHALL be printed
