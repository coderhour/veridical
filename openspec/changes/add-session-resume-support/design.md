# Design: Session Resume Support

## Overview
This change adds the ability to resume an existing Jules session instead of always creating a new one. The design prioritizes simplicity and minimal code changes.

## Architecture

### Current Flow (without session ID)
```
run() → DISPATCHING → create_session() → POLLING → SYNCING → VERIFYING → [loop or SUCCESS]
```

### New Flow (with session ID)
```
run(session_id) → POLLING (skip dispatch) → SYNCING → VERIFYING → [loop or SUCCESS]
                                                                      ↓
                                              (if loop) → DISPATCHING → create_session() → POLLING → ...
```

## Key Decisions

### 1. First Iteration Only
The session ID is only used for the **first iteration**. If verification fails and the loop continues, subsequent iterations create new sessions as usual. This avoids complexity around sending follow-up messages to existing sessions.

**Rationale:** 
- Jules sessions may be in various states (completed, failed, waiting for input)
- Attempting to "continue" a completed session requires different API semantics
- Keeping the first iteration as a "catch up" and then proceeding normally is cleaner

### 2. No State Persistence
We do not persist the session ID or iteration state between CLI invocations. Each `veri run` is independent.

**Rationale:**
- Simpler implementation
- User explicitly provides session ID when needed
- State files can become stale or corrupted

### 3. Session Validation
We rely on the poller to validate the session. If the session ID is invalid or the session is in an unrecoverable state, the poller will timeout or return a failure.

**Rationale:**
- Avoids adding a pre-check API call
- Natural error handling through existing code paths

## Interface Changes

### CLI
```bash
# Resume an existing session
veri run "Continue working on the bug fix" --session-id abc123

# Same thing with shortcut
veri run "Continue working on the bug fix" -s abc123

# Normal usage (unchanged)
veri run "Fix the login bug"
```

### Supervisor
```python
async def run(
    self, 
    task_description: str, 
    session_id: str | None = None
) -> LoopResult:
    ...
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Invalid session ID | Poller returns error, loop fails gracefully |
| Session already completed | Poller returns immediately, sync proceeds |
| Session in FAILED state | Poll result indicates failure, loop may retry with new session |
| Session still running | Poller waits for completion as usual |
