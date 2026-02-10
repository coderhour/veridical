# Change: Add End-to-End and Integration Tests

## Why
Veridical now has two supervisor paths (Jules-based `Supervisor` and `LocalSupervisor`), a worker protocol abstraction, local provider presets, gtr worktree integration, report generation, and LLM-based feedback analysis. The project defines three test levels (unit, integration, E2E) but the E2E tier (`tests/e2e/`) is empty and integration coverage for newer components is incomplete. Without broad E2E and integration coverage, regressions in component interactions go undetected.

## What Changes
- Add E2E tests for the Jules-based supervisor loop (success, retry, circuit breaker, stagnation, state persistence, resume)
- Add E2E tests for the local supervisor loop (`LocalSupervisor` with mock worker commands)
- Add integration tests for local provider CLI features (resolution, auto-detection, dry-run, gtr flag)
- Add integration tests for report generation (WorkLogWriter → ReportGenerator → formatters)
- Add integration tests for LLM feedback and log analysis (RLM chunking, heuristic fallback)
- Add integration tests for worklog round-trip and resume state persistence
- Provide shared fixtures: temporary git repos, mock configs, mock workers
- Use pytest markers (`@pytest.mark.e2e`, `@pytest.mark.integration`, `@pytest.mark.slow`) for selective execution

## Impact
- Affected specs: `supervisor`
- Affected code: `tests/e2e/`, `tests/integration/`, `tests/conftest.py`, `pyproject.toml`
- No changes to production code — test-only change
