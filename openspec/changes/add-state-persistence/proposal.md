# Change: Add State Persistence and Graceful Shutdown

## Why
When the supervisor loop is interrupted (Ctrl+C, network failure, crash), all progress is lost. Users must restart from scratch, wasting API costs and time. The existing `--session-id` flag helps but doesn't persist iteration count, error context, or branch state.

## What Changes
- Add `.veridical_state.json` file for persisting loop state
- Implement SIGINT/SIGTERM handlers for graceful shutdown
- Add `veri resume` CLI command to continue from saved state
- Persist iteration count, session ID, error context, and work branch

## Impact
- Affected specs: supervisor, cli
- Affected code: `src/veridical/supervisor/loop.py`, `src/veridical/supervisor/state.py`, `src/veridical/cli/run.py`
