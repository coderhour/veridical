# Implementation Tasks

## Phase 1: CLI Extension
- [x] 1.1 Add `--session-id` / `-s` option to `veri run` command in `src/veridical/cli/run.py`.
- [x] 1.2 Pass the session ID through to the supervisor via `run_supervisor()`.
- [x] 1.3 Update CLI help text to document the resume behavior.

## Phase 2: Supervisor Resume Logic
- [x] 2.1 Modify `Supervisor.run()` to accept an optional `session_id` parameter.
- [x] 2.2 When `session_id` is provided, skip the dispatching step and go directly to polling.
- [x] 2.3 Use the provided session ID for polling, syncing, and verification.
- [x] 2.4 If verification fails and the loop continues, create a new session for subsequent iterations (normal behavior).

## Phase 3: Testing
- [x] 3.1 Add unit test for CLI parsing of `--session-id` / `-s` option.
- [x] 3.2 Add unit test for `Supervisor.run()` with pre-existing session ID.
- [x] 3.3 Add unit test verifying that dispatching is skipped when session ID is provided.
- [x] 3.4 Add unit test verifying normal iteration continues after resume if verification fails.

## Phase 4: Documentation
- [x] 4.1 Update `README.md` to document the `--session-id` / `-s` option with usage examples.
