# Change: Add Session Resume Support

## Why
Currently, `veri run` always creates a new Jules session for each invocation. This is wasteful when:
- A session was interrupted (timeout, network failure, user abort)
- A session completed but local verification failed and the user wants to retry with the same session context
- The user wants to continue iterating on an existing session rather than starting fresh

By allowing users to specify an existing session ID, Veridical can resume polling an in-progress session or send follow-up messages to trigger additional work, reducing API costs and preserving session context.

## What Changes
- Add `--session-id` option to the `veri run` CLI command
- When a session ID is provided:
  - Skip the session creation step (dispatching)
  - Go directly to polling the specified session
  - Continue with sync, verify, and iteration loop as usual
- When no session ID is provided, behavior remains unchanged (create a new session)
- Iteration counter starts fresh (the resumed session's internal state is opaque to Veridical)

## Impact
- Affected specs: `cli`, `supervisor`
- Affected code: `src/veridical/cli/run.py`, `src/veridical/supervisor/loop.py`
