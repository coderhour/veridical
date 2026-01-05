## 1. Progress Display
- [ ] 1.1 Create `ProgressReporter` class using Rich library
- [ ] 1.2 Implement spinner with current state display
- [ ] 1.3 Add elapsed time counter
- [ ] 1.4 Add iteration counter display (e.g., "Iteration 2/10")

## 2. Activity Streaming
- [ ] 2.1 Add `--verbose` / `-v` flag to `veri run` command
- [ ] 2.2 Implement `stream_activities()` method in Poller
- [ ] 2.3 Parse activity entries for human-readable output
- [ ] 2.4 Display file operations (reading, writing, testing)

## 3. Status Summary
- [ ] 3.1 Show last activity summary on each poll
- [ ] 3.2 Display files being modified when available
- [ ] 3.3 Show test results from Jules' internal runs
- [ ] 3.4 Add compact mode for non-TTY environments

## 4. Integration
- [ ] 4.1 Pass progress reporter to Supervisor and Poller
- [ ] 4.2 Update state transitions to trigger progress updates
- [ ] 4.3 Ensure clean output on interruption (hide spinner)

## 5. Testing
- [ ] 5.1 Add unit tests for ProgressReporter formatting
- [ ] 5.2 Add integration test with mock activities
- [ ] 5.3 Test non-TTY fallback behavior
