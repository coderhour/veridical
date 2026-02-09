# Change: Add Local Loop Mode

## Why
Today Veridical is tightly coupled to Google Jules as the execution backend — every run requires a cloud VM, API key, and patch download. But the core value proposition (define verification rules, run AI, verify locally, loop until passing) works equally well with local AI tools that edit files directly in the working tree. A local loop mode enables immediate, zero-latency verify-and-fix cycles without any cloud dependency, making Veridical useful for the most common AI coding workflow: human gives task → local AI codes → verification runs → AI fixes failures.

## What Changes
- Add a new `veri local` CLI command that runs a local verify-and-loop cycle
- Introduce a `LocalRunner` component that executes a configurable shell command (e.g., `claude-code`, `aider`, a custom script) as the "worker"
- The local loop skips DISPATCHING/POLLING/SYNCING states — it runs the worker command, then verifies, then feeds errors back to the worker
- Add `local` section to `.veridical.yaml` for configuring the worker command, environment, and working directory
- Reuse existing `Verifier`, `CircuitBreaker`, and work log infrastructure
- Support both interactive (worker runs in foreground) and non-interactive (worker runs as subprocess) modes

## Impact
- Affected specs: `supervisor`, `cli`, `config`
- Affected code: `src/veridical/supervisor/`, `src/veridical/cli/`, `src/veridical/config/`
- No breaking changes to existing Jules-based workflow
