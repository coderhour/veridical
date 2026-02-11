## ADDED Requirements

### Requirement: Parallel Subcommand
The CLI SHALL provide a `parallel` subcommand that decomposes a task and dispatches it to multiple concurrent workers.

#### Scenario: Parallel with Task Description
- **WHEN** running `veri parallel "Implement user auth and add API tests"`
- **THEN** it SHALL decompose the task into independent subtasks
- **AND** it SHALL dispatch each subtask to a concurrent worker in its own gtr worktree
- **AND** it SHALL display progress for all workers
- **AND** on completion it SHALL merge results and run final verification

#### Scenario: Parallel with OpenSpec Changes
- **WHEN** running `veri parallel --from-specs`
- **AND** there are multiple open OpenSpec changes with incomplete tasks
- **THEN** it SHALL create one subtask per open change
- **AND** it SHALL dispatch them in parallel

#### Scenario: Parallel Max Workers Override
- **WHEN** running `veri parallel "task" --max-workers 5`
- **THEN** it SHALL override the configured `parallel.max_workers` with 5
- **AND** no more than 5 workers SHALL run concurrently

#### Scenario: Parallel Dry Run
- **WHEN** running `veri parallel "task" --dry-run`
- **THEN** it SHALL display the decomposition plan showing each subtask and estimated files
- **AND** it SHALL NOT create any worktrees or dispatch any workers

#### Scenario: Parallel Missing gtr
- **WHEN** running `veri parallel` and `git gtr` is not installed
- **THEN** it SHALL display an error with gtr install instructions
- **AND** it SHALL exit with code 1

### Requirement: Status Dashboard
The `veri status` command SHALL support a `--dashboard` flag for real-time multi-session monitoring.

#### Scenario: Dashboard Display
- **WHEN** running `veri status --dashboard`
- **AND** parallel workers are active
- **THEN** it SHALL display a live-updating table with columns: Worker ID, Subtask, Status, Iteration, Duration
- **AND** it SHALL refresh every 2 seconds

#### Scenario: Dashboard No Active Workers
- **WHEN** running `veri status --dashboard`
- **AND** no parallel workers are active
- **THEN** it SHALL display "No active parallel sessions"
