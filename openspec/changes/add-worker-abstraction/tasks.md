## 1. Worker Protocol Definition
- [ ] 1.1 Create `src/veridical/worker/` module with `__init__.py`
- [ ] 1.2 Define `Worker` Protocol class with methods: `dispatch(task, error_context) -> WorkResult`, `poll(handle) -> PollResult`, `sync(handle) -> SyncResult`
- [ ] 1.3 Define `WorkResult`, `WorkHandle` models for worker output
- [ ] 1.4 Define `WorkerConfig` base model for worker-specific configuration

## 2. Jules Worker Implementation
- [ ] 2.1 Create `src/veridical/worker/jules.py` implementing `JulesWorker(Worker)`
- [ ] 2.2 Move dispatch logic from `Dispatcher` into `JulesWorker.dispatch()`
- [ ] 2.3 Move polling logic from `Poller` into `JulesWorker.poll()`
- [ ] 2.4 Move sync logic from `Synchronizer` into `JulesWorker.sync()`
- [ ] 2.5 Preserve all existing Jules-specific behavior (auto-approve, patch download, branch management)

## 3. Supervisor Refactor
- [ ] 3.1 Modify `Supervisor.__init__` to accept a `Worker` instance instead of `JulesClient`
- [ ] 3.2 Refactor `Supervisor.run()` loop to use `Worker` protocol methods
- [ ] 3.3 Remove direct references to `Dispatcher`, `Poller`, `Synchronizer` from the supervisor loop
- [ ] 3.4 Ensure circuit breaker and work log integration remain unchanged

## 4. Worker Registry and Configuration
- [ ] 4.1 Add `worker` section to `VeridicalConfig` with `backend: str` (default: `jules`) and backend-specific config
- [ ] 4.2 Implement `WorkerRegistry` that maps backend names to worker classes
- [ ] 4.3 Update `veri run` CLI to resolve worker from config and pass to `Supervisor`

## 5. Testing
- [ ] 5.1 Add unit tests for `Worker` protocol compliance (using a mock worker)
- [ ] 5.2 Add unit tests for `JulesWorker` (verifying existing behavior is preserved)
- [ ] 5.3 Add unit tests for `WorkerRegistry` resolution
- [ ] 5.4 Update existing supervisor tests to use the new `Worker` interface

## 6. Documentation
- [ ] 6.1 Update README with worker abstraction section
- [ ] 6.2 Update HOW_IT_WORKS.md architecture diagram to show Worker layer
- [ ] 6.3 Add migration guide for the breaking `Supervisor` constructor change
