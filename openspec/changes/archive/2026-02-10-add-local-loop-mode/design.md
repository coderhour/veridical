## Context
Veridical's core loop (dispatch → verify → feedback → iterate) is currently only available via the Jules cloud API. Local AI tools (Claude Code, Aider, Cursor, custom scripts) edit files directly in the working tree, eliminating the need for polling, patch download, and branch synchronization. A local loop mode provides a simpler, faster, zero-dependency path to the same autonomous quality assurance outcome.

## Goals / Non-Goals
- **Goals**:
  - Enable verify-and-loop cycles with any local command that modifies files
  - Reuse existing Verifier, CircuitBreaker, and WorkLog infrastructure
  - Support both interactive (TTY-attached) and non-interactive (subprocess) worker modes
  - Keep the local loop independent of Jules — no API key required
- **Non-Goals**:
  - Replacing the Jules-based remote loop (both modes coexist)
  - Building a full agent framework (the worker command is a black box)
  - Git branch isolation for local mode (worker edits the working tree directly)

## Decisions
- **LocalRunner as a thin subprocess wrapper**: The worker is invoked as a shell command. Veridical does not manage the AI tool's internals — it only provides the task description and error context, then verifies the result. This keeps the abstraction simple and tool-agnostic.
- **Error context delivery via environment variable**: The `VERIDICAL_ERROR_CONTEXT` env var is set before each worker invocation with the verification feedback from the previous iteration. This is the simplest cross-tool mechanism. Workers can also read from a file path set in `VERIDICAL_ERROR_FILE`.
- **Simplified state machine**: The local loop uses IDLE → RUNNING → VERIFYING → SUCCESS/FAILED, skipping DISPATCHING/POLLING/SYNCING since there is no remote session to manage.
- **No branch isolation in local mode**: Unlike the Jules flow, local mode operates directly on the current working tree. The user is responsible for their own Git workflow. This avoids complexity and matches how developers actually use local AI tools.

## Risks / Trade-offs
- **Risk**: Worker command may hang or consume excessive resources → Mitigated by `worker_timeout` configuration and circuit breaker.
- **Risk**: Interactive mode cannot capture stdout for logging → Mitigated by logging only exit code and verification results in interactive mode.
- **Trade-off**: No branch isolation means failed iterations leave changes in the working tree → Acceptable because this matches normal local development workflow; users can `git stash` or `git checkout` manually.

## Open Questions
- Should `veri local` support `--watch` mode that re-runs verification on file changes without re-invoking the worker?
- Should the error context also be written to a temporary file for workers that cannot read environment variables?
