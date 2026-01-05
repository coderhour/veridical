# Change: Add Polling Observability and Progress Reporting

## Why
The Poller logs state changes but provides no structured progress to the CLI. Long waits (5-10 min) with minimal feedback frustrate users. Users have no visibility into what Jules is actually working on.

## What Changes
- Add Rich progress bars/spinners during polling phase
- Display activity summaries from `get_activities()` showing files being worked on
- Add `--verbose` flag to stream Jules activity log in real-time
- Show estimated time remaining based on elapsed time patterns

## Impact
- Affected specs: poller, cli
- Affected code: `src/veridical/poller/monitor.py`, `src/veridical/cli/run.py`, `src/veridical/cli/output.py`
