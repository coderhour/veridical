## Context
Veridical supports gtr worktree isolation for a single session, but multi-agent parallel execution requires orchestrating N concurrent supervisor instances, each in its own worktree, with conflict-aware merging. This is a cross-cutting change introducing a new orchestration layer on top of existing supervisor and gtr components.

## Goals / Non-Goals
- Goals:
  - Orchestrate N concurrent LocalSupervisor instances in isolated gtr worktrees
  - Decompose compound tasks into independent subtasks (heuristic and optional LLM-based)
  - Merge completed subtask branches with conflict detection
  - Run final integrated verification on the merged result
  - Provide real-time dashboard view of all active sessions
- Non-Goals:
  - Parallel Jules API sessions in v1 (Jules API may have rate limits; focus on local workers first)
  - Automatic conflict resolution via LLM (report conflicts for human resolution in v1)
  - Distributed execution across multiple machines

## Decisions
- **gtr required for parallel mode**: Each worker needs an isolated worktree. If gtr is not installed, `veri parallel` exits with an error.
- **asyncio.TaskGroup for concurrency**: Use Python 3.11+ `TaskGroup` to manage concurrent supervisor instances. Each runs in its own `asyncio.Task`.
- **Sequential merge after completion**: After all workers finish, merge branches sequentially to detect conflicts incrementally rather than all-at-once.
- **Final verification is mandatory**: After merging all subtask branches, run the full quality gate suite once to catch integration issues.
- Alternatives considered:
  - `multiprocessing` for true parallelism → Unnecessary; I/O-bound work (subprocess calls) is well-served by `asyncio`.
  - Automatic LLM-based conflict resolution → Too risky for v1; better to report and let the human decide.

## Risks / Trade-offs
- **Merge conflicts between subtasks** → Mitigated by sequential merge with conflict reporting. Preserved worktrees enable manual resolution.
- **Resource exhaustion with many workers** → `max_workers` config caps concurrency (default: 3).
- **Task decomposition quality** → Heuristic decomposition may produce non-independent subtasks. LLM-based decomposition improves this but adds cost.

## Open Questions
- Should the decomposer use an LLM by default, or only when `--smart-decompose` is passed?
- Should failed subtasks block other subtasks, or should they continue independently?
- What is the right default for `max_workers`? (Proposed: 3, based on Anthropic's recommendation of 5 local sessions on a MacBook)
