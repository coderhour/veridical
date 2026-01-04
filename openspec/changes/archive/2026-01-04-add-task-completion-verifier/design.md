# Design: Task Completion Verifier

## Context
Veridical implements a supervisory loop that ensures Jules' output meets quality standards. Standard quality gates (tests, linters) ensure the code *works* and is *clean*, but they don't ensure the code is *complete* according to the user's multi-step request.

## Goals
- Enforce strict adherence to the implementation plan defined in `tasks.md`.
- Prevent "early exits" where the agent thinks it's done because the tests passed.
- Provide clear feedback to the agent about which tasks were missed.

## Decisions
- **Parser Choice**: Use a simple regex-based parser for Markdown checklists. No need for complex AST parsing for this specific use case.
- **Exclusion Keywords**: Initially hardcode "manual test" and "integration test". In the future, this could be configurable.
- **Context Awareness**: The verifier needs to know which change ID is being worked on. This information is already available in the `Supervisor` but needs to be passed down or auto-detected by the `Verifier`.

## Risks / Trade-offs
- **False Positives**: An agent might check the box without actually doing the work. This gate doesn't verify the *quality* of the task, only the *declaration* of completion. It is a necessary but not sufficient condition.
- **Synchronization**: If Jules updates `tasks.md` in the remote VM, but Veridical fails to sync that specific file correctly, the verification will fail. Veridical must ensure `tasks.md` is part of the synchronized patch.

## Open Questions
- Should we also verify `proposal.md` or `spec deltas`? (For now, just `tasks.md` as it is the most actionable).
