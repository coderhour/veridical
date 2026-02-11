## 1. Orchestrator Module
- [x] 1.1 Create `src/veridical/orchestrator/__init__.py` with module exports
- [x] 1.2 Implement `TaskDecomposer` in `src/veridical/orchestrator/decomposer.py` (split a large task into independent subtasks using heuristics or LLM)
- [x] 1.3 Implement `ParallelDispatcher` in `src/veridical/orchestrator/dispatcher.py` (spawn N concurrent LocalSupervisor instances, each in its own gtr worktree)
- [x] 1.4 Implement `ConflictResolver` in `src/veridical/orchestrator/resolver.py` (merge subtask branches, detect conflicts, attempt auto-resolution)
- [x] 1.5 Implement `OrchestratorLoop` in `src/veridical/orchestrator/loop.py` (main orchestration: decompose -> dispatch -> monitor -> merge -> verify)

## 2. Configuration
- [x] 2.1 Add `ParallelConfig` model to `src/veridical/config/schema.py` with `max_workers`, `merge_strategy`, `final_verification` fields
- [x] 2.2 Add `parallel: ParallelConfig` field to `VeridicalConfig`
- [x] 2.3 Add `parallel` section to `.veridical.yaml.template` with documented options

## 3. CLI Commands
- [x] 3.1 Create `src/veridical/cli/parallel.py` with `veri parallel` Typer command
- [x] 3.2 Implement task input: accept task string, or read all open OpenSpec changes, or accept a task list file
- [x] 3.3 Implement `--max-workers` flag to override config
- [x] 3.4 Implement `--dry-run` flag to show decomposition without executing
- [x] 3.5 Add `--dashboard` flag to `veri status` for real-time multi-session monitoring
- [x] 3.6 Register `parallel` command in main CLI app

## 4. Supervisor Extension
- [x] 4.1 Ensure `LocalSupervisor` can be instantiated multiple times concurrently (no shared mutable state)
- [x] 4.2 Each parallel worker instance SHALL use its own gtr worktree (require gtr for parallel mode)
- [x] 4.3 Implement final integrated verification after all subtask branches are merged

## 5. Tests
- [x] 5.1 Unit tests for `TaskDecomposer` with sample compound tasks
- [x] 5.2 Unit tests for `ConflictResolver` with mock merge scenarios (clean merge, conflict)
- [x] 5.3 Integration test: 2 parallel workers complete independent subtasks and merge successfully
- [x] 5.4 Integration test: parallel mode with conflict detection and reporting
- [x] 5.5 Integration test: final integrated verification runs after merge
- [x] 5.6 Integration test: `veri parallel --dry-run` shows decomposition plan
