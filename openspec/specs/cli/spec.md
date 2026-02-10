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

### Requirement: gtr Worktree Flag
The `veri local` command SHALL support a `--gtr` flag to enable git worktree isolation via gtr.

#### Scenario: gtr Flag Enabled
- **WHEN** running `veri local "Fix bug" --gtr`
- **THEN** the system SHALL create a git worktree via `git gtr new` with an auto-generated branch name
- **AND** the worker command SHALL execute inside the worktree directory
- **AND** the verifier SHALL run against the worktree path

#### Scenario: gtr Flag Disabled by Default
- **WHEN** running `veri local "Fix bug"` without `--gtr`
- **AND** `local.gtr_enabled` is not set or is `false`
- **THEN** the system SHALL run in the current working directory as before
- **AND** no worktree SHALL be created

#### Scenario: gtr Flag with Config Enabled
- **WHEN** running `veri local "Fix bug"` without `--gtr`
- **AND** `local.gtr_enabled` is `true` in config
- **THEN** the system SHALL enable gtr worktree isolation
- **AND** behavior SHALL be identical to passing `--gtr`

#### Scenario: gtr Not Installed
- **WHEN** running `veri local "Fix bug" --gtr`
- **AND** `git gtr` is not available on PATH
- **THEN** the system SHALL display an error with gtr install instructions (link to https://github.com/coderabbitai/git-worktree-runner)
- **AND** it SHALL exit with code 1

#### Scenario: gtr Branch Name from Spec
- **WHEN** running `veri local` with `--gtr`
- **AND** a spec named "add-user-auth" is selected
- **THEN** the auto-generated branch name SHALL be `veri/add-user-auth`
- **AND** the branch name SHALL be displayed to the user

#### Scenario: gtr Branch Name from Task Description
- **WHEN** running `veri local "Fix login validation bug" --gtr`
- **AND** no spec is selected
- **THEN** the auto-generated branch name SHALL be derived from the task description (e.g., `veri/fix-login-validation-bug`)
- **AND** the branch name SHALL contain only lowercase letters, numbers, and hyphens

#### Scenario: gtr Merge and Cleanup on Success
- **WHEN** the local loop completes successfully with gtr enabled
- **THEN** the system SHALL attempt to merge the worktree branch back to the starting branch (the branch the user was on when `veri local` was invoked)
- **AND** if the merge succeeds, it SHALL display a message confirming the merge
- **AND** if the merge succeeds and `local.gtr_auto_cleanup` is `true`, it SHALL remove the worktree via `git gtr rm`
- **AND** if the merge succeeds and `local.gtr_auto_cleanup` is `false`, it SHALL keep the worktree intact

#### Scenario: gtr Merge Conflict on Success
- **WHEN** the local loop completes successfully with gtr enabled
- **AND** the automatic merge fails due to conflicts
- **THEN** the system SHALL abort the merge and keep the worktree intact
- **AND** it SHALL display the worktree path and branch name
- **AND** it SHALL instruct the user to merge manually (e.g., `cd <worktree-path>` or `git merge veri/<branch>`)
- **AND** it SHALL exit with code 0 (the work itself succeeded)

#### Scenario: gtr Preserved on Failure
- **WHEN** the local loop fails with gtr enabled
- **THEN** the system SHALL NOT attempt to merge the worktree branch
- **AND** it SHALL keep the worktree intact for inspection or continued work
- **AND** it SHALL display the worktree path and branch name so the user can navigate to it

### Requirement: Local Command Interactive Flow
The `veri local` command SHALL provide an interactive flow when run without a task argument, including provider resolution, spec selection, and task input.

#### Scenario: No Arguments With Single Provider and Open Specs
- **WHEN** running `veri local` without any arguments
- **AND** exactly one provider is detected on PATH
- **AND** there are OpenSpec changes with incomplete tasks
- **THEN** the system SHALL auto-select the detected provider
- **AND** it SHALL display the interactive spec selection menu
- **AND** upon spec selection it SHALL auto-generate task description as "Implement spec <selected-name>"

#### Scenario: No Arguments With Open Specs and None Selected
- **WHEN** running `veri local` without any arguments
- **AND** the user selects "None" from the spec selection menu
- **THEN** the system SHALL prompt the user for a free-text task description
- **AND** it SHALL use the entered text as the task

#### Scenario: No Arguments With No Open Specs
- **WHEN** running `veri local` without any arguments
- **AND** there are no OpenSpec changes with incomplete tasks
- **THEN** the system SHALL prompt the user for a free-text task description
- **AND** it SHALL use the entered text as the task

#### Scenario: No Arguments With Empty Task Input
- **WHEN** running `veri local` without any arguments
- **AND** the user provides an empty task description at the prompt
- **THEN** the system SHALL display an error: "No task description provided"
- **AND** it SHALL exit with code 1

#### Scenario: Task Argument Provided With Open Specs
- **WHEN** running `veri local "Fix bug"`
- **AND** "Fix bug" does not match any spec name
- **AND** there are OpenSpec changes with incomplete tasks
- **THEN** the system SHALL show the interactive spec selection menu
- **AND** the menu SHALL include a "None" option to skip task verification

#### Scenario: Task Argument Matches Spec Name
- **WHEN** running `veri local "Implement spec add-feature"`
- **AND** `add-feature` matches an existing OpenSpec change
- **THEN** it SHALL automatically select that spec for task verification
- **AND** it SHALL NOT show the interactive selection menu

### Requirement: Local Command No-Spec Flag
The `veri local` command SHALL support `--no-spec` / `--skip-tasks` flags to bypass spec selection.

#### Scenario: Skip Spec Selection
- **WHEN** running `veri local "Fix bug" --no-spec`
- **THEN** it SHALL bypass spec selection completely
- **AND** it SHALL NOT show the interactive selection menu
- **AND** it SHALL proceed with other quality gates

### Requirement: Local Provider CLI Option
The `veri local` command SHALL support a `--provider` / `-p` option for selecting a named local provider.

#### Scenario: Provider Flag Usage
- **WHEN** running `veri local "Fix bug" --provider claude-code`
- **THEN** the system SHALL configure the local runner using the `claude-code` provider preset
- **AND** the provider's default command, mode, and error delivery strategy SHALL be used

#### Scenario: Provider Flag Overrides Config
- **WHEN** running `veri local --provider gemini-cli`
- **AND** `local.provider` in config is set to `claude-code`
- **THEN** the CLI `--provider` flag SHALL take precedence over the config file value

#### Scenario: Provider with Worker Flag
- **WHEN** running `veri local --provider claude-code --worker "custom-command"`
- **THEN** the custom worker command SHALL take precedence over the provider's default command
- **AND** the provider's error delivery strategy SHALL still be used

#### Scenario: Unknown Provider Flag
- **WHEN** running `veri local --provider unknown-tool`
- **THEN** the system SHALL display an error listing available providers
- **AND** it SHALL exit with code 1

### Requirement: Provider List Command
The `veri local` command SHALL support a `--list-providers` flag to display available providers.

#### Scenario: List Providers Output
- **WHEN** running `veri local --list-providers`
- **THEN** the system SHALL display a table of registered providers
- **AND** each row SHALL show provider name, description, and whether the tool is detected on PATH
- **AND** it SHALL exit with code 0 without running the loop

#### Scenario: List Providers with Detection
- **WHEN** running `veri local --list-providers`
- **AND** `claude` is available on PATH but `gemini` is not
- **THEN** `claude-code` SHALL show as "detected" or with a checkmark
- **AND** `gemini-cli` SHALL show as "not found" or with a cross mark

### Requirement: Provider Auto-Detection
The `veri local` command SHALL support auto-detecting available providers when no provider or worker is specified.

#### Scenario: Auto-Detect Single Provider
- **WHEN** running `veri local "Fix bug"` without `--provider` or `--worker`
- **AND** `local.worker_command` is empty and `local.provider` is not set
- **AND** exactly one provider is detected on PATH
- **THEN** the system SHALL auto-select that provider
- **AND** it SHALL display a message indicating which provider was auto-detected

#### Scenario: Auto-Detect Multiple Providers
- **WHEN** running `veri local "Fix bug"` without `--provider` or `--worker`
- **AND** `local.worker_command` is empty and `local.provider` is not set
- **AND** multiple providers are detected on PATH
- **THEN** the system SHALL display an interactive selection menu listing detected providers
- **AND** the user SHALL select one to proceed

#### Scenario: No Provider Detected
- **WHEN** running `veri local "Fix bug"` without `--provider` or `--worker`
- **AND** `local.worker_command` is empty and `local.provider` is not set
- **AND** no providers are detected on PATH
- **THEN** the system SHALL display an error with instructions to install a supported tool or use `--worker`
- **AND** it SHALL exit with code 1

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

### Requirement: Local Subcommand
The CLI SHALL provide a `local` subcommand to run a local verify-and-loop cycle.

#### Scenario: Local Command with Task
- **WHEN** running `veri local "Fix the failing tests"`
- **THEN** it SHALL start the local supervisor loop with the given task description
- **AND** it SHALL use the configured worker command from `.veridical.yaml`

#### Scenario: Local Command with Worker Override
- **WHEN** running `veri local "Fix the tests" --worker "aider --message '{task}'"`
- **THEN** it SHALL use the provided worker command instead of the configured default
- **AND** `{task}` placeholders in the command SHALL be replaced with the task description

#### Scenario: Local Command with Shared Flags
- **WHEN** running `veri local` with `--max-iterations`, `--dry-run`, `--verbose`, or `--no-spec`
- **THEN** these flags SHALL behave identically to the `run` command

#### Scenario: Local Command without Worker
- **WHEN** running `veri local "Fix the tests"`
- **AND** no worker command is configured or provided via `--worker`
- **THEN** it SHALL display an error: "No worker command configured. Set `local.worker_command` in .veridical.yaml or use --worker"
- **AND** it SHALL exit with code 1

#### Scenario: Local Command No API Key Required
- **WHEN** running `veri local`
- **THEN** it SHALL NOT require the `JULES_API_KEY` environment variable

