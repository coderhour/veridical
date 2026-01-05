# Proposal: Add Dynamic Spec Detection

## Status
🟡 Draft

## Problem Statement

Currently, the task_completion quality gate in Veridical uses a **hardcoded path** to a tasks.md file:

```python
path="openspec/changes/add-task-completion-verifier/tasks.md"
```

This means regardless of which OpenSpec change the user is working on, Veridical always verifies the same outdated tasks.md file instead of the one for the current change. This defeats the purpose of tracking task completion.

## Proposed Solution

Implement **dynamic spec detection** that:

1. **Scans for open specs**: Find all OpenSpec changes with incomplete tasks in `openspec/changes/*/tasks.md`
2. **Matches from task description**: If the task description contains a spec name (e.g., "Implement spec add-configurable-backoff-strategy"), automatically select that spec's tasks.md
3. **Interactive selection**: If no spec is matched but open specs exist, prompt the user to select one (or none for bug fixes)
4. **Zero-argument mode**: Allow `veri run` with no arguments, prompting user to select a spec and auto-generating the task description as "Implement spec <name>"

## User Stories

### Story 1: Explicit Spec in Task
**As a** developer running `veri run "Implement spec add-configurable-backoff-strategy"`
**I want** Veridical to automatically detect and verify `openspec/changes/add-configurable-backoff-strategy/tasks.md`
**So that** task completion is correctly tracked for the work I'm doing

### Story 2: Ambiguous Task with Open Specs
**As a** developer running `veri run "Fix some bugs"` when there are open specs
**I want** Veridical to show me the list of specs with open tasks and let me choose
**So that** I can associate my work with the right spec (or none if it's unrelated)

### Story 3: Zero-Argument Run
**As a** developer who wants to implement a spec
**I want** to simply run `veri run` and select from available specs
**So that** I don't have to remember spec names or type long descriptions

### Story 4: No Open Specs
**As a** developer running `veri run "Fix login bug"` with no open specs
**I want** Veridical to proceed without task completion verification
**So that** bug fixes and ad-hoc work aren't blocked

## Scope

### In Scope
- Scan `openspec/changes/*/tasks.md` for incomplete tasks
- Parse spec name from task description patterns like "Implement spec <name>"
- Interactive spec selection UI using Rich/Typer
- Optional task argument on `veri run`
- Auto-generate task description from spec selection
- Update verifier to use dynamically detected tasks.md path

### Out of Scope
- Changes to OpenSpec CLI or format
- Multi-spec selection (one spec per run)
- Auto-detecting spec from git branch name

## Design Considerations

### Spec Name Matching
The system should attempt to match spec names from task descriptions using patterns:
- "Implement spec <name>"
- "implement <name>"
- "<name>" (exact match against change IDs)

### Interactive Selection Flow
```
$ veri run

Found 3 specs with open tasks:
  [1] add-configurable-backoff-strategy (5 tasks remaining)
  [2] add-extended-language-templates (10 tasks remaining)
  [3] implement-rlm-local-log-analysis (8 tasks remaining)
  [0] None (bug fix / no spec)

Select spec [0-3]: 1

Starting task: Implement spec add-configurable-backoff-strategy
```

### Task Completion Gate Integration
The verifier config should support a special `path: auto` setting that triggers dynamic detection:

```yaml
verifier:
  quality_gates:
    - name: task_completion
      type: task_completion
      path: auto  # Dynamic detection
```

## Success Criteria

1. Running `veri run "Implement spec add-configurable-backoff-strategy"` correctly verifies `openspec/changes/add-configurable-backoff-strategy/tasks.md`
2. Running `veri run` with no arguments shows interactive spec selection
3. Running `veri run "Fix bug"` with open specs prompts for spec selection
4. Running `veri run "Fix bug"` with no open specs proceeds without task verification
5. All existing tests continue to pass

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| CI/automation can't use interactive mode | Support `--no-spec` flag to skip task verification |
| Spec name parsing is fragile | Use fuzzy matching and allow fallback to selection |
| Breaking change for existing users | Maintain backward compatibility with explicit `path:` in config |
