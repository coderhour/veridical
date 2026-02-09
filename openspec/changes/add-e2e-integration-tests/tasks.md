## 1. Test Infrastructure
- [ ] 1.1 Create `tests/e2e/conftest.py` with fixtures for temporary git repos, mock configs, and mock API responses
- [ ] 1.2 Create `MockJulesClient` that returns deterministic session responses and patches
- [ ] 1.3 Create helper functions to generate known-good patches (all gates pass) and known-bad patches (specific gates fail)
- [ ] 1.4 Add `e2e` and `integration` pytest markers to `pyproject.toml`

## 2. Happy Path E2E Tests
- [ ] 2.1 Test: full loop succeeds on first iteration (dispatch → poll → sync → verify → SUCCESS)
- [ ] 2.2 Test: full loop succeeds after one failed verification iteration (verify fails → feedback → retry → SUCCESS)
- [ ] 2.3 Test: verify that the final commit exists on the work branch after success
- [ ] 2.4 Test: verify that `.veridical_state.json` is cleaned up after success

## 3. Failure Path E2E Tests
- [ ] 3.1 Test: circuit breaker trips after max_iterations
- [ ] 3.2 Test: circuit breaker trips after max_consecutive_failures
- [ ] 3.3 Test: stagnation detection trips circuit breaker (identical patches)
- [ ] 3.4 Test: patch application failure returns FAILED result immediately
- [ ] 3.5 Test: API error during polling returns FAILED result

## 4. State Persistence E2E Tests
- [ ] 4.1 Test: state file is created at start of iteration
- [ ] 4.2 Test: `resume_from_state=True` restores iteration count and session ID
- [ ] 4.3 Test: resumed session continues from saved state

## 5. Integration Tests (Component Interactions)
- [ ] 5.1 Test: Synchronizer creates and cleans up iteration branches correctly
- [ ] 5.2 Test: Verifier runs quality gates against actual file changes in a temp repo
- [ ] 5.3 Test: CircuitBreaker integrates correctly with Supervisor state transitions
- [ ] 5.4 Test: WorkLogWriter produces valid JSONL entries during a supervisor run

## 6. Test Configuration
- [ ] 6.1 Update `pyproject.toml` to exclude `e2e` tests from default `pytest` run
- [ ] 6.2 Add CI-friendly test commands to README (e.g., `pytest -m "not e2e"`, `pytest -m e2e`)
