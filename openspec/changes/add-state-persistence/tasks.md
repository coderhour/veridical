## 1. State Model
- [x] 1.1 Create `LoopState` model with iteration, session_id, error_context, work_branch fields
- [x] 1.2 Add `save()` and `load()` methods for JSON persistence
- [x] 1.3 Define state file location (`.veridical_state.json` in repo root)

## 2. Signal Handling
- [x] 2.1 Add SIGINT handler to supervisor loop
- [x] 2.2 Add SIGTERM handler for graceful termination
- [x] 2.3 Ensure state is saved before exit on signal
- [x] 2.4 Clean up iteration branches on graceful shutdown

## 3. Resume Logic
- [x] 3.1 Implement state restoration in `Supervisor.run()`
- [x] 3.2 Skip completed iterations based on saved state
- [x] 3.3 Restore error context for feedback continuity
- [x] 3.4 Validate saved session ID is still valid before resuming

## 4. CLI Integration
- [x] 4.1 Add `veri resume` command that loads saved state
- [x] 4.2 Add `--force-new` flag to ignore saved state
- [x] 4.3 Display saved state info on startup if state file exists
- [x] 4.4 Clear state file on successful completion or explicit abort

## 5. Testing
- [x] 5.1 Add unit tests for state serialization/deserialization
- [x] 5.2 Add integration test simulating interruption and resume
- [x] 5.3 Add test for state file cleanup on success
