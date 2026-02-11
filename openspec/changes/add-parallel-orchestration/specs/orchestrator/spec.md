## ADDED Requirements

### Requirement: Orchestrator Module Structure
The system SHALL provide a `veridical.orchestrator` module for decomposing tasks and managing parallel worker execution.

#### Scenario: Module Import
- **WHEN** importing `from veridical.orchestrator import OrchestratorLoop, TaskDecomposer, ParallelDispatcher`
- **THEN** the import SHALL succeed without errors

### Requirement: Task Decomposer
The system SHALL provide a `TaskDecomposer` class that splits compound tasks into independent subtasks.

#### Scenario: Heuristic Decomposition
- **WHEN** calling `decomposer.decompose(task_description, repo_path)` with a compound task
- **THEN** it SHALL return a list of `Subtask` objects, each with a `description`, `estimated_files`, and `independence_score`
- **AND** subtasks SHALL be ordered by independence (most independent first)

#### Scenario: Single Task Passthrough
- **WHEN** calling `decomposer.decompose(task_description, repo_path)` with a simple, non-decomposable task
- **THEN** it SHALL return a single `Subtask` containing the original task description

#### Scenario: OpenSpec-Based Decomposition
- **WHEN** calling `decomposer.decompose_from_specs(change_ids)` with a list of OpenSpec change IDs
- **THEN** it SHALL read each change's `tasks.md` and create one `Subtask` per change
- **AND** each subtask description SHALL be "Implement spec {change_id}"

### Requirement: Parallel Dispatcher
The system SHALL provide a `ParallelDispatcher` class that spawns concurrent `LocalSupervisor` instances in isolated gtr worktrees.

#### Scenario: Dispatch N Workers
- **WHEN** calling `await dispatcher.dispatch(subtasks, config)` with N subtasks
- **THEN** it SHALL create N gtr worktrees (one per subtask)
- **AND** it SHALL instantiate N `LocalSupervisor` instances (one per worktree)
- **AND** it SHALL run all supervisors concurrently using `asyncio.TaskGroup`
- **AND** the number of concurrent workers SHALL NOT exceed `config.parallel.max_workers`

#### Scenario: Worker Completion Tracking
- **WHEN** parallel workers are running
- **THEN** the dispatcher SHALL track each worker's status (running, succeeded, failed)
- **AND** it SHALL return a `ParallelResult` containing per-subtask outcomes

#### Scenario: gtr Requirement
- **WHEN** `veri parallel` is invoked
- **AND** `git gtr` is not available on PATH
- **THEN** it SHALL display an error: "gtr is required for parallel mode. Install from https://github.com/coderabbitai/git-worktree-runner"
- **AND** it SHALL exit with code 1

### Requirement: Conflict Resolver
The system SHALL provide a `ConflictResolver` class that merges completed subtask branches and detects conflicts.

#### Scenario: Clean Sequential Merge
- **WHEN** calling `resolver.merge(subtask_branches, target_branch)`
- **AND** all merges apply cleanly
- **THEN** it SHALL merge each subtask branch sequentially into the target branch
- **AND** it SHALL return a `MergeResult` with `success=True` and a list of merged branches

#### Scenario: Merge Conflict Detected
- **WHEN** calling `resolver.merge(subtask_branches, target_branch)`
- **AND** a merge conflict occurs between subtask branches
- **THEN** it SHALL abort the conflicting merge
- **AND** it SHALL return a `MergeResult` with `success=False`, the conflicting branches, and conflict details
- **AND** it SHALL preserve all worktrees for manual resolution

### Requirement: Orchestrator Loop
The system SHALL provide an `OrchestratorLoop` class that coordinates the full parallel workflow: decompose, dispatch, merge, and verify.

#### Scenario: Full Parallel Workflow
- **WHEN** calling `await orchestrator.run(task_description)`
- **THEN** it SHALL decompose the task into subtasks
- **AND** it SHALL dispatch subtasks in parallel
- **AND** it SHALL wait for all workers to complete
- **AND** it SHALL merge successful subtask branches
- **AND** it SHALL run a final integrated verification on the merged result
- **AND** it SHALL return an `OrchestratorResult` with per-subtask and overall outcomes

#### Scenario: Partial Success
- **WHEN** some subtasks succeed and others fail
- **THEN** it SHALL report which subtasks succeeded and which failed
- **AND** it SHALL NOT attempt to merge failed subtask branches
- **AND** it SHALL preserve failed worktrees for inspection

#### Scenario: Final Integrated Verification
- **WHEN** all subtask branches have been merged
- **THEN** it SHALL run the full quality gate suite (`Verifier.run_all()`) on the merged result
- **AND** if verification fails, it SHALL report integration issues in the result
