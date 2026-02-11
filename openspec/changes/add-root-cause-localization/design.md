## Context
The current feedback pipeline (`FeedbackGenerator`) sends raw/compressed log output back to the worker. Fault localization is the single highest-leverage improvement for first-iteration success. This change adds a multi-signal localization module that can be used standalone (`veri diagnose`) or integrated into the verify loop feedback path.

## Goals / Non-Goals
- Goals:
  - Extract file:line references from stack traces, AST call graphs, and git blame
  - Produce ranked localization reports with confidence scores
  - Enrich existing `FeedbackGenerator` output without breaking current behavior
  - Provide standalone CLI for debugging outside the supervisor loop
- Non-Goals:
  - Full semantic code search with embeddings (deferred to learning-loop feature)
  - Support for non-Python languages in v1 (AST analysis uses Python's `ast` module)
  - Replacing the existing heuristic/RLM feedback modes (localization augments them)

## Decisions
- **Python `ast` module for call graph analysis**: No new dependency needed. Tree-sitter support can be added later for multi-language.
- **Git blame via subprocess**: Reuse existing `GitOperations` class pattern from `src/veridical/synchronizer/git_ops.py`.
- **Localization is optional**: Integrated via an optional `Localizer` parameter in `FeedbackGenerator`, preserving backward compatibility.
- Alternatives considered:
  - tree-sitter for AST → Deferred; Python `ast` covers the primary use case and avoids a new C dependency.
  - Embedding-based semantic search → Deferred to learning-loop feature; too heavy for v1.

## Risks / Trade-offs
- **AST parsing may fail on syntax errors** → Graceful fallback to stack-trace-only localization.
- **Git blame adds latency** → Blame is run only on files identified by stack trace (narrow scope).
- **Python-only in v1** → Acceptable since Veridical's primary user base is Python projects. Multi-language via tree-sitter is a natural follow-up.

## Open Questions
- Should localization run automatically on every failed iteration, or only when explicitly enabled via config?
- Should confidence scores be exposed in the work log for post-run analysis?
