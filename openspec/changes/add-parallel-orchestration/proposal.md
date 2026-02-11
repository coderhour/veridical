# Change: Add Multi-Agent Parallel Orchestration (`veri parallel`)

## Why
Veridical already supports `gtr` worktree isolation for running sessions in parallel, but it requires the user to manually open multiple terminals. The industry has converged on orchestrator-workers as the dominant agentic pattern (Anthropic runs 5-10 parallel Claude Code sessions routinely). Veridical should orchestrate multiple parallel workers natively — decomposing a large task into independent subtasks, dispatching each to its own worker+worktree, monitoring progress, and merging results with a final integrated verification. A feature that takes 1 hour serially (3 iterations x 20 min) could complete in 25 minutes with parallel subtasks.

## What Changes
- Add a new `veridical.orchestrator` module with `TaskDecomposer`, `ParallelDispatcher`, and `ConflictResolver` classes
- Add a new CLI command `veri parallel` that accepts a task or reads open OpenSpec changes and dispatches them concurrently
- Add a `veri status --dashboard` mode showing all active parallel sessions with progress
- Extend `LocalSupervisor` to be instantiable N times concurrently, each in its own gtr worktree
- Add `ParallelConfig` section to `.veridical.yaml` for max concurrent workers, merge strategy, etc.
- After all subtasks succeed, run a final integrated verification on the merged result

## Impact
- Affected specs: `cli`, `config`, `supervisor`
- New capability: `orchestrator` (new spec)
- Affected code: `src/veridical/orchestrator/` (new), `src/veridical/cli/parallel.py` (new), `src/veridical/local/supervisor.py`, `src/veridical/config/schema.py`
