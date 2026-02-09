## ADDED Requirements

### Requirement: Work Log Module Structure

The system SHALL provide a `veridical.worklog` module for persisting iteration history.

#### Scenario: Module Import

WHEN importing `from veridical.worklog import WorkLogWriter`
THEN the import SHALL succeed without errors

### Requirement: Work Log Entry Model

The system SHALL define a `WorkLogEntry` model capturing the full context of each iteration.

#### Scenario: Entry Structure

WHEN creating a `WorkLogEntry`
THEN it SHALL contain the following fields:
- `timestamp: datetime` - When the entry was recorded
- `iteration: int` - Iteration number
- `session_id: str` - Jules session ID
- `task_description: str` - Original task description
- `error_context: str | None` - Error context from previous iteration
- `prompt_sent: str | None` - The prompt sent to Jules
- `session_status: str` - Status of the Jules session (completed, failed, etc.)
- `verification_passed: bool | None` - Whether verification succeeded
- `verification_errors: str | None` - Verification error summary if failed
- `duration_seconds: float | None` - Time taken for the iteration

#### Scenario: Entry Serialization

WHEN calling `entry.model_dump_json()`
THEN it SHALL return valid JSON with all fields serialized

### Requirement: Work Log Writer

The system SHALL provide a `WorkLogWriter` class for persisting entries to disk.

#### Scenario: Writer Initialization

WHEN instantiating `WorkLogWriter(project_path: Path)`
THEN it SHALL use `project_path / "worklog"` as the log directory
AND it SHALL NOT create the directory until the first write

#### Scenario: Writer Initialization with Custom Directory

WHEN instantiating `WorkLogWriter(project_path: Path, log_dir: str)`
THEN it SHALL use `project_path / log_dir` as the log directory

#### Scenario: Write Entry

WHEN calling `writer.write(entry: WorkLogEntry)`
THEN it SHALL create the directory `worklog/YYYY-MM-DD/` if it does not exist
AND it SHALL append the entry as a JSON line to `worklog/YYYY-MM-DD/iterations.jsonl`

#### Scenario: Date-Based Organization

WHEN multiple entries are written on the same date
THEN they SHALL all be appended to the same `iterations.jsonl` file
AND when entries are written on different dates
THEN they SHALL be written to different date-based directories

### Requirement: Supervisor Work Log Integration

The Supervisor SHALL record iteration details to the work log.

#### Scenario: Iteration Start Logging

WHEN the supervisor starts an iteration
THEN it SHALL record a partial entry with iteration number, task description, and error context

#### Scenario: Iteration End Logging

WHEN the supervisor completes an iteration (success or failure)
THEN it SHALL update the entry with session status, verification result, and duration
AND it SHALL write the complete entry to the work log

#### Scenario: Shutdown Logging

WHEN the supervisor receives a shutdown signal (SIGINT/SIGTERM)
THEN it SHALL write the current incomplete entry to the work log with status "interrupted"

### Requirement: Work Log Configuration

The system SHALL allow work log behavior to be configured.

#### Scenario: Default Configuration

WHEN no `worklog` section is present in `.veridical.yaml`
THEN work logging SHALL be enabled by default
AND the log directory SHALL default to `worklog/`

#### Scenario: Disable Work Log

WHEN `.veridical.yaml` contains `worklog: enabled: false`
THEN the supervisor SHALL NOT write any work log entries

#### Scenario: Custom Log Directory

WHEN `.veridical.yaml` contains `worklog: directory: custom_logs/`
THEN work log entries SHALL be written to `custom_logs/YYYY-MM-DD/iterations.jsonl`
