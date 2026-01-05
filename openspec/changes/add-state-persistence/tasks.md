## 1. State Model
- [ ] 1.1 Create `LoopState` model with iteration, session_id, error_context, work_branch fields
- [ ] 1.2 Add `save()` and `load()` methods for JSON persistence
- [ ] 1.3 Define state file location (`.veridical_state.json` in repo root)

## 2. Signal Handling
- [ ] 2.1 Add SIGINT handler to supervisor loop
- [ ] 2.2 Add SIGTERM handler for graceful termination
- [ ] 2.3 Ensure state is saved before exit on signal
- [ ] 2.4 Clean up iteration branches on graceful shutdown

## 3. Resume Logic
- [ ] 3.1 Implement state restoration in `Supervisor.run()`
- [ ] 3.2 Skip completed iterations based on saved state
- [ ] 3.3 Restore error context for feedback continuity
- [ ] 3.4 Validate saved session ID is still valid before resuming

## 4. CLI Integration
- [ ] 4.1 Add `veri resume` command that loads saved state
- [ ] 4.2 Add `--force-new` flag to ignore saved state
- [ ] 4.3 Display saved state info on startup if state file exists
- [ ] 4.4 Clear state file on successful completion or explicit abort

## 5. Testing
- [ ] 5.1 Add unit tests for state serialization/deserialization
- [ ] 5.2 Add integration test simulating interruption and resume
- [ ] 5.3 Add test for state file cleanup on success
