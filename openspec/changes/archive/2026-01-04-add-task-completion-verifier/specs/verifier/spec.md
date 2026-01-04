## ADDED Requirements

### Requirement: Task Completion Verification

The system SHALL verify that all non-manual tasks in the active `tasks.md` are marked as complete.

#### Scenario: All tasks completed
- **WHEN** all `- [x]` boxes are checked in `tasks.md`
- **THEN** the task-completion gate SHALL pass

#### Scenario: Missing tasks
- **WHEN** there is at least one unchecked `- [ ]` box in `tasks.md`
- **AND** the task description does NOT contain "manual test" or "integration test"
- **THEN** the task-completion gate SHALL fail
- **AND** the feedback SHALL include the descriptions of the incomplete tasks

#### Scenario: Excluded tasks
- **WHEN** an unchecked `- [ ]` box contains "manual test" or "integration test"
- **THEN** it SHALL be ignored by the task-completion gate
- **AND** the gate SHALL pass if all other boxes are checked
