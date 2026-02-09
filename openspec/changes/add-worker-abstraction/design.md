## Context
The Supervisor currently orchestrates Jules-specific components (Dispatcher, Poller, Synchronizer) directly. This makes it impossible to swap in a different AI backend without rewriting the supervisor loop. The Worker abstraction introduces a clean boundary between "what the supervisor does" (verify, loop, circuit-break) and "how the AI agent works" (dispatch, poll, sync).

## Goals / Non-Goals
- **Goals**:
  - Define a `Worker` Protocol that any AI backend can implement
  - Refactor existing Jules integration into `JulesWorker` without behavior changes
  - Make `Supervisor` backend-agnostic
  - Enable future workers (local CLI tools, other cloud agents) via simple protocol implementation
- **Non-Goals**:
  - Implementing non-Jules workers in this change (that's `add-local-loop-mode`)
  - Changing the verification or circuit breaker logic
  - Supporting multiple concurrent workers in a single run

## Decisions
- **Python Protocol (structural subtyping)**: Use `typing.Protocol` instead of ABC. This allows duck-typing — any class with the right methods works, no inheritance required. This is more Pythonic and allows third-party workers without importing Veridical.
- **Three-method interface**: `dispatch(task, error_context) -> WorkResult` covers session creation and feedback sending. `poll(handle) -> PollResult` covers waiting for completion. `sync(handle) -> SyncResult` covers fetching and applying changes. This maps cleanly to the existing supervisor states.
- **WorkHandle as opaque token**: The `dispatch` method returns a `WorkHandle` that is passed to `poll` and `sync`. For Jules, this wraps the session ID. For local workers, it might be a PID or a no-op. The supervisor never inspects the handle's internals.
- **JulesWorker composes existing components**: Rather than deleting `Dispatcher`, `Poller`, and `Synchronizer`, `JulesWorker` wraps them. This preserves all existing logic and tests while satisfying the new protocol.
- **Worker resolution via config**: The `worker.backend` config field selects the worker class from a registry. Default is `jules` for backward compatibility.

## Risks / Trade-offs
- **Risk**: Breaking change to `Supervisor.__init__` → Mitigated by updating all call sites in the same change and providing a migration guide.
- **Risk**: Over-abstraction making debugging harder → Mitigated by keeping the Worker protocol minimal (3 methods) and preserving existing component classes inside JulesWorker.
- **Trade-off**: WorkHandle is opaque, so the supervisor can't log backend-specific details → Acceptable; workers can log their own details internally.

## Migration Plan
1. Introduce `Worker` protocol and `JulesWorker` alongside existing code
2. Update `Supervisor.__init__` to accept `Worker`
3. Update `veri run` CLI to construct `JulesWorker` and pass it
4. Verify all existing tests pass
5. Remove direct Dispatcher/Poller/Synchronizer imports from supervisor module

## Open Questions
- Should `Worker` expose a `cancel()` method for graceful shutdown?
- Should `WorkResult` include cost/token metadata for observability?
