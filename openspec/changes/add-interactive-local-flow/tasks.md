## 1. CLI Implementation
- [x] 1.1 Add `--no-spec` / `--skip-tasks` flag to `veri local` command
- [x] 1.2 Add spec detection logic: `find_open_specs()` + `match_spec_from_description()` + `select_spec()`
- [x] 1.3 Add free-text task prompt when no task provided and no spec selected
- [x] 1.4 Wire `tasks_file` from spec selection into `run_local_supervisor()`
- [x] 1.5 Remove hardcoded "Local autonomous task" fallback; replace with interactive prompt

## 2. Testing
- [x] 2.1 Add integration test: `veri local` with no args triggers spec selection or task prompt
- [x] 2.2 Add integration test: `veri local --no-spec "Fix bug"` skips spec selection
- [x] 2.3 Add integration test: `veri local "Implement spec <name>"` auto-matches spec

## 3. Documentation
- [x] 3.1 Update README local mode section with interactive flow examples
