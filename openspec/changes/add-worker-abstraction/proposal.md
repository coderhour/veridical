# Change: Add Worker Abstraction Layer

## Why
Veridical is currently hardwired to Google Jules as the sole AI worker. The `Supervisor` directly instantiates `Dispatcher`, `Poller`, and `Synchronizer` — all of which assume Jules-specific APIs (create session, poll status, download patch). This tight coupling prevents using Veridical with other AI coding agents (Claude Code, Aider, OpenAI Codex, custom scripts, future agents). Introducing a `Worker` protocol decouples the supervisor loop from any specific backend, making Veridical a universal verify-and-loop orchestrator.

## What Changes
- Define a `Worker` protocol (Python Protocol class) with a standard interface: `dispatch`, `poll`, `sync`, and `get_error_context`
- Refactor the existing Jules integration into a `JulesWorker` that implements the `Worker` protocol
- Modify `Supervisor` to accept a `Worker` instance instead of directly using `Dispatcher`/`Poller`/`Synchronizer`
- Add a `worker` configuration section to `.veridical.yaml` for selecting and configuring the active worker backend
- **BREAKING**: `Supervisor.__init__` signature changes — it accepts a `Worker` instead of separate `JulesClient`/`Dispatcher`/`Poller` instances

## Impact
- Affected specs: `supervisor`, `api`, `dispatcher`, `config`
- Affected code: `src/veridical/supervisor/loop.py`, `src/veridical/dispatcher/`, `src/veridical/poller/`, `src/veridical/synchronizer/`, `src/veridical/config/`
- **BREAKING**: `Supervisor` constructor signature changes
- **BREAKING**: `veri run` must resolve the worker backend from config before constructing the supervisor
