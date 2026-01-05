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

The `run` command SHALL support optional task description with automatic spec detection.

#### Scenario: Run Command with No Arguments

WHEN running `veri run` without any arguments
AND there are OpenSpec changes with incomplete tasks
THEN it SHALL display an interactive spec selection menu
AND it SHALL auto-generate task description as "Implement spec <selected-name>"
AND it SHALL proceed with the supervisor loop using the generated task

#### Scenario: Run Command with No Arguments and No Open Specs

WHEN running `veri run` without any arguments
AND there are no OpenSpec changes with incomplete tasks
THEN it SHALL display an error: "No task provided and no open specs found"
AND it SHALL exit with code 1

#### Scenario: Run Command with Spec in Task Description

WHEN running `veri run "Implement spec <name>"`
AND `<name>` matches an existing OpenSpec change
THEN it SHALL automatically select that spec for task verification
AND it SHALL NOT show the interactive selection menu

#### Scenario: Run Command with Unmatched Task and Open Specs

WHEN running `veri run "<task>"` with a task that doesn't match any spec name
AND there are OpenSpec changes with incomplete tasks
THEN it SHALL show the interactive spec selection menu
AND the menu SHALL include an option to skip task verification

#### Scenario: Run Command with No-Spec Flag

WHEN running `veri run "<task>" --no-spec` or `veri run "<task>" --skip-tasks`
THEN it SHALL bypass task verification completely
AND it SHALL NOT show the interactive selection menu
AND it SHALL proceed with other quality gates

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

The CLI SHALL provide a `config` subcommand for configuration management.

#### Scenario: Config Init with Template

WHEN running `veridical config init --template <name>`
THEN it SHALL accept template names: `python`, `nodejs`, `elixir`, `java`, `go`, `rust`, `typescript`, `ruby`, `php`, `dotnet`
AND it SHALL generate the corresponding language-specific configuration file

#### Scenario: Config Template Command with Template Option

WHEN running `veridical config template --template <name>`
THEN it SHALL accept template names: `python`, `nodejs`, `elixir`, `java`, `go`, `rust`, `typescript`, `ruby`, `php`, `dotnet`
AND it SHALL output the corresponding template content to stdout

### Requirement: Interactive Spec Selection

The CLI SHALL provide an interactive menu for selecting OpenSpec changes.

#### Scenario: Spec Selection Menu Display

WHEN the spec selection menu is triggered
THEN it SHALL display all OpenSpec changes with incomplete tasks
AND it SHALL show the incomplete task count for each spec
AND it SHALL include a "None" option for skipping task verification
AND it SHALL prompt the user to select by number

#### Scenario: Spec Selection User Input

WHEN the user selects a spec by number
THEN it SHALL return the corresponding spec's tasks.md path
AND it SHALL generate task description if not provided

#### Scenario: Spec Selection Cancel

WHEN the user cancels selection (Ctrl+C or invalid input)
THEN it SHALL display "Aborted"
AND it SHALL exit with code 0

