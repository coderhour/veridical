# Design: Supervisor Control Loop

## 1. Architectural Overview

The Supervisor is the central orchestrator of Project Veridical. It implements a **Feedback Control Loop** pattern designed to converge a probabilistic agent (Jules) toward a deterministic outcome (Local Quality Gates).

### 1.1 The Control Loop

The loop follows a strict state machine:

```mermaid
graph TD
    IDLE -->|run(task)| DISPATCHING
    DISPATCHING -->|session_id| POLLING
    POLLING -->|COMPLETED| SYNCING
    POLLING -->|FAILED| FAILED
    
    SYNCING -->|patch_applied| VERIFYING
    SYNCING -->|patch_failed| FAILURE_ANALYSIS
    
    VERIFYING -->|pass| SUCCESS
    VERIFYING -->|fail| FAILURE_ANALYSIS
    
    FAILURE_ANALYSIS -->|can_retry| DISPATCHING
    FAILURE_ANALYSIS -->|max_retries| FAILED
```

## 2. Component Interactions

### 2.1 Dispatcher: Source Detection
The `Dispatcher` must automatically detect the context.
- **Input**: Local CWD
- **Logic**: `git remote get-url origin` -> `git@github.com:owner/repo` -> `sources/github/owner/repo`
- **Fallback**: Error if not a git repo or no remote.

### 2.2 Synchronizer: Patch Strategy
Data flow for code synchronization:
1. **Remote**: Jules creates a PR or internal diff.
2. **Fetch**: Veridical uses `GET /sessions/{id}/diff` (or equivalent) to get unified diff.
3. **Isolation**: `git checkout -b veridical/iter-N`
4. **Apply**: `git apply patch.diff`
5. **Verify**: Check `git status` for clean application.

### 2.3 Verifier: Feedback Compression
Raw logs are too large for LLM context. The `FeedbackGenerator` implements "Lossy Compression" focused on utility. Since Veridical is language-agnostic, this uses generic heuristics:
- **Heuristic Parsing**: Identify common error patterns (lines containing `error`, `fail`, `exception`, `fatal` case-insensitive).
- **Smart Truncation**: Retain the "head" (context) and the "tail" (summary), while aggressively compressing the middle if no error signals are found.
- **Strategy**: Prioritize lines with error keywords > standard output. Truncate to config limit (e.g., 2000 chars).

## 3. State Management

The `Supervisor` maintains the `IterationContext`:
```python
@dataclass
class IterationContext:
    iteration: int
    task_description: str
    error_context: str | None
    session_history: List[str]
```
This context is passed to the `Dispatcher` to construct the "Sandwich Prompt" for the next iteration.

## 4. Circuit Breaker

The circuit breaker enforces termination to prevent infinite costs:
1. **Max Iterations**: Hard limit (default 10).
2. **Stagnation**: If `diff_hash` is identical for 3 iterations, stop.
3. **Consecutive Failures**: If patch application fails 3 times, stop.
