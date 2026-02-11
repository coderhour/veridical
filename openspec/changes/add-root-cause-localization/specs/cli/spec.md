## ADDED Requirements

### Requirement: Diagnose Subcommand
The CLI SHALL provide a `diagnose` subcommand for standalone root-cause localization of code failures.

#### Scenario: Diagnose from Error Text
- **WHEN** running `veri diagnose --error "Traceback (most recent call last): ..."`
- **THEN** it SHALL parse the error text for stack traces and file references
- **AND** it SHALL run localization analysis against the current repository
- **AND** it SHALL display a ranked list of candidate root-cause locations with confidence scores

#### Scenario: Diagnose from Test Name
- **WHEN** running `veri diagnose --test "test_login_validation"`
- **THEN** it SHALL run the specified test to capture its failure output
- **AND** it SHALL parse the output for stack traces
- **AND** it SHALL display a localization report for the failure

#### Scenario: Diagnose from Log File
- **WHEN** running `veri diagnose --file path/to/error.log`
- **THEN** it SHALL read the file contents
- **AND** it SHALL parse for stack traces and error patterns
- **AND** it SHALL display a localization report

#### Scenario: Diagnose Output Format
- **WHEN** running `veri diagnose` with any input source
- **THEN** the output SHALL display candidates in a Rich table with columns: Rank, File:Line, Function, Confidence, Evidence
- **AND** candidates SHALL be sorted by descending confidence score

#### Scenario: Diagnose JSON Output
- **WHEN** running `veri diagnose --format json`
- **THEN** it SHALL output the localization report as JSON
- **AND** the JSON SHALL contain the same fields as the table output

#### Scenario: Diagnose No Results
- **WHEN** running `veri diagnose` and no localization candidates are found
- **THEN** it SHALL display "No root-cause candidates found in the error output"
- **AND** it SHALL exit with code 0
