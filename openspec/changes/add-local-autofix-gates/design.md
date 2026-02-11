## Context

Quality gates like `ruff format --check` and `ruff check --fix` detect issues that have deterministic, tool-based fixes. Today, when these gates fail, the error is fed back to the LLM worker (Claude Code, Gemini CLI, etc.) which wastes an iteration fixing something a local command can resolve in milliseconds.

Jules operates on a remote VM and its API does not support uploading patches, so autofix is only viable for `veri local` and `veri verify`.

## Goals / Non-Goals

- **Goals:**
  - Allow quality gates to declare an optional `fix_command` that runs automatically when the gate fails
  - Run autofix only in local contexts (`veri local` loop, `veri verify --fix`)
  - Re-verify the gate after autofix to confirm the fix succeeded
  - Keep the feature backward-compatible (no `fix_command` = current behavior)

- **Non-Goals:**
  - Supporting autofix for Jules mode (`veri run`) — Jules has no patch upload API
  - Auto-committing fixes — the fix modifies the working tree; the next worker iteration or user handles commits
  - Running fix commands that require LLM involvement — this is strictly for deterministic tool fixes

## Decisions

- **Gate-level `fix_command` field:** Each `QualityGate` gets an optional `fix_command: str` field. This keeps autofix configuration co-located with the gate it fixes, making it easy to reason about. The `fix_command` is only used when `autofix_enabled` is true on the `Verifier` (default `True`). Jules mode explicitly disables it.
  - *Alternative: Separate `autofix` config section.* Rejected because it decouples the fix from the gate, making configuration harder to maintain and reason about.

- **Autofix runs between verification and feedback generation:** In the local supervisor loop, after `run_all()` detects failures, the verifier attempts autofix on gates that have `fix_command`. If any fix commands ran, the verifier re-runs those specific gates. Only remaining failures are fed back to the LLM worker.
  - *Alternative: Pre-verify fix phase (always run fix commands before gates).* Rejected because it runs fix commands even when the gate would pass, adding unnecessary overhead.

- **`veri verify --no-fix` flag:** Autofix is enabled by default for `veri verify`. The `--no-fix` flag allows disabling it when the user wants check-only behavior.

- **Single retry per gate:** After running `fix_command`, the gate is re-run exactly once. If it still fails, the failure stands. This prevents infinite fix loops.

## Risks / Trade-offs

- **Stale fix commands:** If the `fix_command` is misconfigured (e.g., wrong path), it will silently fail and the gate failure proceeds normally. Mitigation: log a warning when `fix_command` exits non-zero.
- **Security:** Fix commands run with full local permissions. Mitigation: these are user-configured commands in `.veridical.yaml`, same trust model as existing `command` gates.

## Open Questions

- Should `fix_command` support a timeout separate from the gate's `timeout`? Initial proposal: reuse the gate's existing `timeout` field for simplicity.
