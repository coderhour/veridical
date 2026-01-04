# Proposal: Implement Supervisor Business Logic

## 1. Context & Problem Statement

Project Veridical has successfully established its structural foundation. The core components (`Supervisor`, `Dispatcher`, `Poller`, `Synchronizer`, `Verifier`) exist as classes with interfaces, but they are currently disconnected. The main control loop in `supervisor/loop.py` is a skeleton that simply returns a "Not implemented" result. 

To make the system functional, we need to implement the business logic that orchestrates the autonomous quality assurance loop. This involves wiring the components together to enable the `DISPATCHING → POLLING → SYNCING → VERIFYING` cycle.

## 2. Proposed Solution

Implement the core business logic for the Supervisor and its satellite components to enable a fully functional autonomous loop.

### 2.1 Supervisor Logic
- Implement the state machine in `Supervisor.run()` that transitions through:
  1. **DISPATCHING**: Construct prompt and create Jules session.
  2. **POLLING**: Wait for Jules to complete work.
  3. **SYNCING**: Retrieve and apply code patches to isolation branches.
  4. **VERIFYING**: Run quality gates and analyze results.
  5. **DECIDING**: Loop with feedback if failed, or merge and exit if passed.

### 2.2 Dispatcher Enhancements
- Implement **Git Repo Auto-Detection**: Automatically determine `sources/github/owner/repo` from the local git remote.
- Implement **Dynamic Constraint Injection**: Update `AGENTS.md` context or prompts with ephemeral constraints based on previous errors.

### 2.3 Synchronizer Logic
- Implement **Patch Retrieval**: Fetch diffs/patches from the Jules API (via `activities` or session result).
- Implement **Branch Management**: Create `veridical/iter-N` branches and merge successful iterations to `main`.

### 2.4 Verifier Enhancements
- Implement **Feedback Generation**: Parse stdout/stderr from failed quality gates into structured, token-efficient error context for the next prompt.

## 3. Scope Definition

| In Scope | Out of Scope |
| :--- | :--- |
| `Supervisor.run()` implementation and state management | UI/Web Dashboard |
| `Dispatcher` git remote parsing | GitHub Actions Integration |
| `Synchronizer` patch retrieval and application logic | Parallel "Duel Mode" |
| `Verifier` feedback generation (error summarization) | Complex merge conflict resolution (basic only) |
| End-to-End integration tests |  |

## 4. Risk Analysis

### Technical Risks
- **Infinite Loops**: The agent may get stuck making the same mistake.
  - *Mitigation*: Ensure `CircuitBreaker` (already scaffolded) is correctly wired into the loop to halt execution after `max_iterations` or stagnation.
- **Context Window Overflow**: Passing full test logs to Jules may exceed token limits.
  - *Mitigation*: Implement smart truncation in `FeedbackGenerator` to only send relevant error sections.
- **Git State Desync**: Local state may change while Jules is working.
  - *Mitigation*: Enforce rigorous branch isolation (`veridical/iter-N`) and check for upstream conflicts before merging.

## 5. Success Criteria

- [ ] `veridical run "task"` executes a full loop cycle (mocked or real).
- [ ] Supervisor correctly transitions through all states.
- [ ] Git repository is correctly detected from `git remote`.
- [ ] Patches are applied to isolation branches.
- [ ] Failed verification produces meaningful error feedback.
- [ ] Successful verification triggers merge to main.
- [ ] `veridical status` shows accurate session info.
