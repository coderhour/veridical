## 1. Local Runner Component
- [x] 1.1 Create `src/veridical/local/` module with `__init__.py`
- [x] 1.2 Implement `LocalRunner` class that executes a shell command as the AI worker
- [x] 1.3 Support passing error context to the worker via environment variable or stdin
- [x] 1.4 Support interactive mode (worker runs in foreground TTY) and subprocess mode
- [x] 1.5 Capture worker exit code and stdout/stderr for logging

## 2. Local Supervisor Loop
- [x] 2.1 Implement `LocalSupervisor` class that orchestrates the local verify-and-fix cycle
- [x] 2.2 Reuse existing `Verifier` for quality gate execution
- [x] 2.3 Reuse existing `CircuitBreaker` for loop termination
- [x] 2.4 Implement simplified state machine: IDLE → RUNNING → VERIFYING → SUCCESS/FAILED
- [x] 2.5 Feed verification error context back to worker on each iteration
- [x] 2.6 Integrate with `WorkLogWriter` for iteration logging

## 3. Configuration
- [x] 3.1 Add `local` section to `VeridicalConfig` with `worker_command`, `worker_timeout`, `mode` (interactive/subprocess), and `error_env_var` fields
- [x] 3.2 Add defaults: `worker_command: ""`, `worker_timeout: 600`, `mode: subprocess`, `error_env_var: VERIDICAL_ERROR_CONTEXT`
- [x] 3.3 Update `.veridical.yaml.template` with local section and examples

## 4. CLI Integration
- [x] 4.1 Add `veri local` command with `task` argument and `--worker` option
- [x] 4.2 Support `--max-iterations`, `--dry-run`, `--verbose`, `--no-spec` flags (reuse from `run`)
- [x] 4.3 Display iteration progress and verification results using existing `ProgressReporter`

## 5. Testing
- [x] 5.1 Add unit tests for `LocalRunner` (subprocess execution, error context passing)
- [x] 5.2 Add unit tests for `LocalSupervisor` (loop logic, circuit breaker integration)
- [x] 5.3 Add integration test with a mock worker script that fixes a known error

## 6. Documentation
- [x] 6.1 Update README with local loop mode section and examples
- [x] 6.2 Add local mode section to HOW_IT_WORKS.md
