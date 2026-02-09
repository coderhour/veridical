## ADDED Requirements

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
