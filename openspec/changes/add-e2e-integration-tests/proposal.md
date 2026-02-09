# Change: Add End-to-End Integration Tests

## Why
The supervisor loop is the most critical and complex component in Veridical — it orchestrates state transitions, git branching, patch application, verification, circuit breaker logic, and signal handling. Currently there are unit tests for individual components but no end-to-end tests that exercise the full loop from `veri run` through to a SUCCESS or FAILED result. Without E2E coverage, regressions in component interactions go undetected. The project's own `project.md` defines three test levels (unit, integration, E2E) but the E2E tier is empty.

## What Changes
- Create a `MockWorker` test fixture that produces deterministic patches (known-good and known-bad)
- Add E2E tests that run the full supervisor loop against the mock worker in a temporary git repository
- Test key scenarios: success on first iteration, success after retry, circuit breaker trip, stagnation detection, graceful shutdown (SIGINT), state persistence and resume
- Add a `conftest.py` with shared fixtures for temporary repos, mock configs, and mock workers
- Add pytest markers (`@pytest.mark.e2e`, `@pytest.mark.integration`) for selective test execution

## Impact
- Affected specs: `supervisor`
- Affected code: `tests/e2e/`, `tests/integration/`, `tests/conftest.py`
- No changes to production code — test-only change
