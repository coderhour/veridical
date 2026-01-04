# cli Specification

## Purpose
TBD - created by archiving change scaffold-foundation. Update Purpose after archive.
## Requirements
### Requirement: CLI Module Structure

The system SHALL provide a `veridical.cli` module implementing the command-line interface.

#### Scenario: Module Import

WHEN importing `from veridical.cli import app`
THEN the import SHALL succeed without errors

#### Scenario: CLI Entry Point

WHEN running `veridical` from the command line
THEN it SHALL invoke the Typer application

### Requirement: Help Command

The system SHALL display help information when invoked with `--help`.

#### Scenario: Root Help

WHEN running `veridical --help`
THEN it SHALL display usage information
AND it SHALL list all available subcommands

#### Scenario: Subcommand Help

WHEN running `veridical <subcommand> --help`
THEN it SHALL display help specific to that subcommand

### Requirement: Version Command

The system SHALL display version information.

#### Scenario: Version Flag

WHEN running `veridical --version`
THEN it SHALL display the package version from pyproject.toml

### Requirement: Fix Subcommand

The system SHALL provide a `fix` subcommand to initiate the quality loop.

#### Scenario: Fix Command Interface

WHEN running `veridical fix "Fix the login bug"`
THEN it SHALL accept a task description as a positional argument
AND it SHALL start the supervisor loop

#### Scenario: Fix Command Options

WHEN running `veridical fix`
THEN it SHALL accept `--max-iterations` to limit loop iterations
AND it SHALL accept `--dry-run` to simulate without API calls
AND it SHALL accept `--verbose` for detailed output

### Requirement: Verify Subcommand

The system SHALL provide a `verify` subcommand to run local quality gates.

#### Scenario: Verify Command

WHEN running `veridical verify`
THEN it SHALL execute all configured quality gates
AND it SHALL display pass/fail results
AND it SHALL exit with code 0 if all pass, 1 otherwise

### Requirement: Status Subcommand

The system SHALL provide a `status` subcommand to check active sessions.

#### Scenario: Status Command

WHEN running `veridical status`
THEN it SHALL display a table of active Jules sessions
AND it SHALL show session ID, status, and iteration count

#### Scenario: No Active Sessions

WHEN running `veridical status` with no active sessions
THEN it SHALL display "No active sessions"

### Requirement: Config Subcommand

The system SHALL provide a `config` subcommand to manage configuration.

#### Scenario: Config Show

WHEN running `veridical config show`
THEN it SHALL display the current effective configuration
AND it SHALL indicate which values came from defaults vs config file

#### Scenario: Config Init

WHEN running `veridical config init`
THEN it SHALL create a `.veridical.yaml` template in the current directory
AND it SHALL NOT overwrite an existing file without `--force`

