# verifier Specification Delta

## MODIFIED Requirements

### Requirement: Task Completion Gate with Auto Path

The task_completion quality gate SHALL support dynamic path detection.

#### Scenario: Auto Path Configuration

WHEN a task_completion gate is configured with `path: auto`
THEN the verifier SHALL use the dynamically detected tasks.md path from the current spec context
AND if no spec is selected, it SHALL skip the task_completion gate

#### Scenario: Explicit Path Configuration

WHEN a task_completion gate is configured with an explicit path (e.g., `path: openspec/changes/foo/tasks.md`)
THEN the verifier SHALL use the explicitly configured path
AND the behavior SHALL remain unchanged from current implementation

#### Scenario: Default Configuration

WHEN the default VerifierConfig is used
THEN the task_completion gate SHALL default to `path: auto`
AND it SHALL integrate with the dynamic spec detection system
