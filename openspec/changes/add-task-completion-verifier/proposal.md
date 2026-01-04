# Change: Add Task Completion Verifier

## Why
Currently, Veridical relies on external quality gates (tests, linters) to verify implementation success. However, an agent might pass all tests while only completing a fraction of the requested tasks in `tasks.md`. This change introduces a default verification step that ensures every non-manual task is explicitly marked as complete in the `tasks.md` file.

## What Changes
- Add a new default quality gate: `task-completion`.
- This gate scans `openspec/changes/<current-change-id>/tasks.md`.
- It verifies that all `- [ ]` items are converted to `- [x]`.
- It excludes tasks that are explicitly marked as `manual test` or `integration test` (which might be handled outside the core loop).
- Integrates this gate into the `Verifier` component as a mandatory check.

## Impact
- Affected specs: `verifier`
- Affected code: `src/veridical/verifier/`, `src/veridical/supervisor/`
