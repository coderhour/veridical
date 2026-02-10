## 1. Test Infrastructure
- [x] 1.1 Add `e2e`, `integration`, and `slow` pytest markers to `pyproject.toml`
- [x] 1.2 Create shared fixtures in `tests/conftest.py` (temp dirs, sample configs, mock git repos)
- [x] 1.3 Create `MockJulesClient` helpers in `tests/integration/test_e2e_supervisor_flow.py` (deterministic session responses and patches)
- [x] 1.4 Create `tests/e2e/conftest.py` with shared E2E fixtures (extract from integration tests)

## 2. Jules Supervisor E2E Tests
- [x] 2.1 Test: full loop succeeds on first iteration (dispatch → poll → sync → verify → SUCCESS)
- [x] 2.2 Test: full loop succeeds after one failed verification iteration (verify fails → feedback → retry → SUCCESS)
- [x] 2.3 Test: verify that the final commit exists on the work branch after success
- [x] 2.4 Test: circuit breaker trips after max_iterations
- [x] 2.5 Test: resume existing session with `--session-id`
- [x] 2.6 Test: branch state is correct at each step of the flow
- [x] 2.7 Test: stagnation detection trips circuit breaker (identical patches)
- [x] 2.8 Test: patch application failure returns FAILED result immediately
- [x] 2.9 Test: API error during polling returns FAILED result
- [x] 2.10 Test: verify that `.veridical_state.json` is cleaned up after success

## 3. Local Supervisor E2E Tests
- [x] 3.1 Test: local loop succeeds after retry (worker → verify fail → worker → verify pass)
- [x] 3.2 Test: local loop circuit breaker trips after max_iterations
- [x] 3.3 Test: local loop with provider-based command construction
- [x] 3.4 Test: local loop worklog entries are written during run

## 4. State Persistence & Resume Tests
- [x] 4.1 Test: supervisor loads state when resuming (`resume_from_state=True`)
- [x] 4.2 Test: state file is deleted on success
- [x] 4.3 Test: resumed session continues from saved iteration count

## 5. Integration Tests (Component Interactions)
- [x] 5.1 Test: WorkLogWriter produces valid JSONL entries (full workflow)
- [x] 5.2 Test: ReportGenerator reads worklog and produces terminal/JSON/HTML reports
- [x] 5.3 Test: LogAnalyzer chunks large logs and calls LLM per chunk (RLM strategy)
- [x] 5.4 Test: FeedbackGenerator end-to-end summarization with LLM
- [x] 5.5 Test: Local provider CLI (list, dry-run, unknown provider error)
- [x] 5.6 Test: Local interactive flow (no-spec, skip-tasks, task prompt)
- [x] 5.7 Test: gtr CLI flag (dry-run branch name, not-installed error)
- [x] 5.8 Test: Supervisor loop integration (basic flow with mock worker)
- [x] 5.9 Test: Verifier integration against actual file changes in temp repo
- [x] 5.10 Test: Work branch creation and cleanup
- [x] 5.11 Test: CircuitBreaker integrates correctly with LocalSupervisor state transitions
- [x] 5.12 Test: Synchronizer creates and cleans up iteration branches correctly (standalone)

## 6. Test Configuration
- [x] 6.1 Markers defined in `pyproject.toml` (`unit`, `integration`, `e2e`, `slow`)
- [x] 6.2 Add CI-friendly test commands to README (e.g., `pytest -m "not e2e"`, `pytest -m e2e`)
