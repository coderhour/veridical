# Implementation Tasks

## Phase 1: Dispatcher & Repo Detection

- [x] 1.1 Implement `GitContext.get_remote_url()` to read local git config
- [x] 1.2 Implement `SourceContext.from_local_git()` factory method
- [x] 1.3 Update `Dispatcher.create_session()` to use auto-detected source if not provided
- [x] 1.4 Write unit tests for git remote parsing and source context generation

## Phase 2: Synchronizer & Patch Retrieval

- [x] 2.1 Implement `JulesClient.download_patch(session_id)` to retrieve diffs
- [x] 2.2 Update `Synchronizer.apply_session_patch()` to coordinate fetch + apply
- [x] 2.3 Implement `BranchManager.safe_merge()` with check for upstream conflicts
- [x] 2.4 Write unit tests for patch retrieval and application flow

## Phase 3: Verifier & Feedback Generation

- [x] 3.1 Implement `FeedbackGenerator.identify_error_lines()` using common keywords
- [x] 3.2 Implement `FeedbackGenerator.compress_log_output()` with head/tail retention
- [x] 3.3 Implement `FeedbackGenerator.generate_context()` to combine multiple command outputs
- [x] 3.4 Write unit tests for log compression with sample outputs from various languages (Go, JS, Python)

## Phase 4: Supervisor Loop Logic

- [x] 4.1 Implement `Supervisor.run()` main execution loop
- [x] 4.2 Wire `CircuitBreaker` checks (iterations, stagnation, consecutive failures)
- [x] 4.3 Implement state transitions and proper logging
- [x] 4.4 Integrate `Dispatcher` -> `Poller` -> `Synchronizer` -> `Verifier` flow
- [x] 4.5 Implement loop carry-over of `error_context` to next iteration

## Phase 5: Integration Testing

- [x] 5.1 Create mocks for `JulesClient` simulating success/failure scenarios
- [x] 5.2 Write integration test for "One-shot Success" (Passes first time)
- [x] 5.3 Write integration test for "Iterative Repair" (Fails once, then passes)
- [x] 5.4 Write integration test for "Circuit Breaker" (Max iterations reached)
