# Change: Add Verification Rule DSL

## Why
The current quality gates in `.veridical.yaml` are limited to shell commands with binary pass/fail outcomes. For the vision of "user defines clear verification rules," this is insufficient. Users need richer primitives: assert that specific files exist, check that only expected files were modified, run gates conditionally based on which files changed, compose gates with AND/OR logic, and interpret non-zero exit codes as warnings vs. failures. A richer verification DSL transforms `.veridical.yaml` from a simple command list into a true verification specification language — the core differentiator of Veridical.

## What Changes
- Add `assertion` gate type: check file existence, content patterns (regex), and JSON/YAML schema validation
- Add `diff_scope` gate type: verify that only files matching allowed glob patterns were modified
- Add `conditional` gate modifier: run a gate only when specific file patterns were modified in the current diff
- Add `composite` gate type: group gates with `all_of` (AND) or `any_of` (OR) logic
- Add `warn_only` flag: gate failure produces a warning instead of blocking the loop
- Add `exit_code_map` option: map specific exit codes to pass/warn/fail outcomes
- Extend the `Verifier` to handle new gate types alongside existing `command` and `task_completion` types

## Impact
- Affected specs: `verifier`, `config`
- Affected code: `src/veridical/verifier/`, `src/veridical/config/schema.py`
- No breaking changes — existing `command` gates continue to work unchanged
