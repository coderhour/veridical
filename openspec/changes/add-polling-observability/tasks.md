## 1. Progress Display
- [x] 1.1 Create `ProgressReporter` class using Rich library
- [x] 1.2 Implement spinner with current state display
- [x] 1.3 Add elapsed time counter
- [x] 1.4 Add iteration counter display (e.g., "Iteration 2/10")

## 2. Activity Streaming
- [x] 2.1 Add `--verbose` / `-v` flag to `veri run` command
- [x] 2.2 Implement `stream_activities()` method in Poller
- [x] 2.3 Parse activity entries for human-readable output
- [x] 2.4 Display file operations (reading, writing, testing)

## 3. Status Summary
- [x] 3.1 Show last activity summary on each poll
- [x] 3.2 Display files being modified when available
- [x] 3.3 Show test results from Jules' internal runs
- [x] 3.4 Add compact mode for non-TTY environments

## 4. Integration
- [x] 4.1 Pass progress reporter to Supervisor and Poller
- [x] 4.2 Update state transitions to trigger progress updates
- [x] 4.3 Ensure clean output on interruption (hide spinner)

## 5. Testing
- [x] 5.1 Add unit tests for ProgressReporter formatting
- [x] 5.2 Add integration test with mock activities
- [x] 5.3 Test non-TTY fallback behavior
