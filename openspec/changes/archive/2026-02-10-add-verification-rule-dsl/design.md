## Context
Veridical's verification system currently supports two gate types: `command` (run a shell command) and `task_completion` (check tasks.md checkboxes). While shell commands are flexible, they require users to write custom scripts for common checks like "did the AI only modify files in `src/`?" or "does `config.json` still validate against its schema?" A richer DSL provides these checks declaratively, reducing the barrier to defining comprehensive verification rules.

## Goals / Non-Goals
- **Goals**:
  - Add assertion, diff_scope, conditional, and composite gate types
  - Add warn_only and exit_code_map for nuanced gate outcomes
  - Maintain full backward compatibility with existing command gates
  - Keep the DSL YAML-native (no custom syntax, just structured YAML)
- **Non-Goals**:
  - Turing-complete scripting in YAML (use `command` gates for complex logic)
  - GUI for building verification rules
  - Runtime gate modification (gates are static per run)

## Decisions
- **Gate type dispatch via registry**: Each gate type (`command`, `task_completion`, `assertion`, `diff_scope`, `composite`) has a corresponding `GateRunner` class. The `Verifier` dispatches to the correct runner based on the `type` field. This is extensible — new gate types can be added by registering a new runner.
- **Three-level severity model**: Gate results are `pass`, `warn`, or `fail`. Only `fail` blocks the loop. `warn` is logged and included in reports but does not trigger a retry iteration. This allows non-critical checks (e.g., code coverage threshold) without blocking progress.
- **Conditional gates use git diff**: The `when_files_changed` modifier compares the current diff's file list against glob patterns. If no matching files were changed, the gate is skipped entirely. This avoids running expensive checks (e.g., `mypy`) when only documentation files changed.
- **Composite gates are recursive**: A `composite` gate contains a list of sub-gates and a mode (`all_of` or `any_of`). Sub-gates can themselves be composites, enabling arbitrarily complex logic trees. In practice, one level of nesting covers most use cases.
- **Exit code map is optional**: By default, exit code 0 = pass, non-zero = fail. The `exit_code_map` allows overriding this (e.g., `{2: warn, 3: pass}`) for tools with non-standard exit codes.

## Risks / Trade-offs
- **Risk**: Complex DSL increases configuration errors → Mitigated by Pydantic validation at load time with clear error messages.
- **Risk**: Composite gates with deep nesting are hard to debug → Mitigated by limiting practical depth and providing clear logging of gate execution tree.
- **Trade-off**: More gate types increase Verifier complexity → Acceptable because each runner is isolated and independently testable.

## Open Questions
- Should assertion gates support checking HTTP endpoints (e.g., health check after deployment)?
- Should diff_scope integrate with the existing `scope_validation` config in the synchronizer, or remain independent?
