# cli Spec Delta

## MODIFIED Requirements

### Requirement: Run Subcommand

The `run` subcommand SHALL support resuming an existing Jules session.

#### Scenario: Run Command Session Resume Option

WHEN running `veri run "task" --session-id <id>` or `veri run "task" -s <id>`
THEN it SHALL accept the `--session-id` / `-s` option as an optional string parameter
AND it SHALL pass the session ID to the supervisor for resumption
AND it SHALL skip creating a new session for the first iteration

#### Scenario: Run Command Without Session ID

WHEN running `veri run "task"` without `--session-id`
THEN behavior SHALL remain unchanged (create a new session)
