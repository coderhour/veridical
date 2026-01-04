# Implementation Tasks

## Phase 1: Task Parser logic
- [ ] 1.1 Implement `TaskParser` to read and parse `tasks.md` files.
- [ ] 1.2 Add logic to detect unchecked boxes `- [ ]` vs checked boxes `- [x]`.
- [ ] 1.3 Add filtering to ignore tasks containing "manual test" or "integration test" (case-insensitive).
- [ ] 1.4 Write unit tests for `TaskParser`.

## Phase 2: Verifier Integration
- [ ] 2.1 Implement `TaskCompletionGate` that uses `TaskParser`.
- [ ] 2.2 Register `TaskCompletionGate` as a default gate in the `Verifier` component.
- [ ] 2.3 Ensure the gate can dynamically find the relevant `tasks.md` based on active change context.
- [ ] 2.4 Update `Verifier.run_all()` to include task completion check.

## Phase 3: Feedback & Error Handling
- [ ] 3.1 Generate specific feedback when tasks are incomplete (listing the exactly missing tasks).
- [ ] 3.2 Ensure failure of this gate triggers a retry loop with the missing tasks context.
- [ ] 3.3 Write integration test for task completion failure scenario.
