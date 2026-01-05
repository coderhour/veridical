# Tasks: Add Dynamic Spec Detection

## Phase 1: Spec Discovery

- [x] Create `src/veridical/openspec/scanner.py` module
  - [x] Implement `find_open_specs()` function to scan `openspec/changes/*/tasks.md`
  - [x] Parse tasks.md files to count incomplete tasks (`- [ ]` pattern)
  - [x] Return list of `OpenSpecInfo(name, path, incomplete_count, total_count)`
  - [x] Add unit tests for scanner

## Phase 2: Spec Matching

- [x] Create `src/veridical/openspec/matcher.py` module
  - [x] Implement `match_spec_from_description(description: str, specs: list[OpenSpecInfo])` function
  - [x] Support patterns: "Implement spec <name>", "implement <name>", exact name match
  - [x] Return matched spec or None
  - [x] Add unit tests for matching logic

## Phase 3: CLI Integration

- [x] Update `src/veridical/cli/run.py`
  - [x] Make `task` argument optional (default to None)
  - [x] Add `--no-spec` / `--skip-tasks` flag to bypass task verification
  - [x] Integrate spec scanner at start of `run()` function
  - [x] If task provided: attempt spec matching
  - [x] If no task or no match: show interactive spec selection
  - [x] Auto-generate task description from selected spec

- [x] Create `src/veridical/cli/spec_selector.py` for interactive selection UI
  - [x] Use Rich for formatted output
  - [x] Show spec list with incomplete task counts
  - [x] Include "None" option for bug fixes
  - [x] Return selected spec or None

## Phase 4: Verifier Integration

- [x] Update `src/veridical/config/schema.py`
  - [x] Allow `path: auto` for task_completion gates
  - [x] Update default to use `path: auto` instead of hardcoded path

- [x] Update `src/veridical/supervisor/loop.py`
  - [x] Pass detected spec path to verifier (or update config dynamically)
  - [x] Store current spec in supervisor state for use by verifier

- [x] Update `src/veridical/verifier/quality_gate.py`
  - [x] Handle `path: auto` by looking up current spec from supervisor context
  - [x] Skip task_completion gate if no spec selected

## Phase 5: Testing

- [x] Add integration test: run with explicit spec in task description
- [x] Add integration test: run with no task triggers selection (mock input)
- [x] Add integration test: run with --no-spec skips task verification
- [x] Add unit tests for each new module

## Phase 6: Documentation

- [x] Update README.md with new usage examples
- [x] Document `--no-spec` flag and interactive mode
- [x] Add example showing zero-argument `veri run`

## Verification

- [x] Run `pytest tests/unit/` - all tests pass
- [x] Run `ruff check src/` - no linting errors
- [x] Run `mypy src/` - no type errors
