## ADDED Requirements

### Requirement: Local Command Interactive Flow
The `veri local` command SHALL provide an interactive flow when run without a task argument, including provider resolution, spec selection, and task input.

#### Scenario: No Arguments With Single Provider and Open Specs
- **WHEN** running `veri local` without any arguments
- **AND** exactly one provider is detected on PATH
- **AND** there are OpenSpec changes with incomplete tasks
- **THEN** the system SHALL auto-select the detected provider
- **AND** it SHALL display the interactive spec selection menu
- **AND** upon spec selection it SHALL auto-generate task description as "Implement spec <selected-name>"

#### Scenario: No Arguments With Open Specs and None Selected
- **WHEN** running `veri local` without any arguments
- **AND** the user selects "None" from the spec selection menu
- **THEN** the system SHALL prompt the user for a free-text task description
- **AND** it SHALL use the entered text as the task

#### Scenario: No Arguments With No Open Specs
- **WHEN** running `veri local` without any arguments
- **AND** there are no OpenSpec changes with incomplete tasks
- **THEN** the system SHALL prompt the user for a free-text task description
- **AND** it SHALL use the entered text as the task

#### Scenario: No Arguments With Empty Task Input
- **WHEN** running `veri local` without any arguments
- **AND** the user provides an empty task description at the prompt
- **THEN** the system SHALL display an error: "No task description provided"
- **AND** it SHALL exit with code 1

#### Scenario: Task Argument Provided With Open Specs
- **WHEN** running `veri local "Fix bug"`
- **AND** "Fix bug" does not match any spec name
- **AND** there are OpenSpec changes with incomplete tasks
- **THEN** the system SHALL show the interactive spec selection menu
- **AND** the menu SHALL include a "None" option to skip task verification

#### Scenario: Task Argument Matches Spec Name
- **WHEN** running `veri local "Implement spec add-feature"`
- **AND** `add-feature` matches an existing OpenSpec change
- **THEN** it SHALL automatically select that spec for task verification
- **AND** it SHALL NOT show the interactive selection menu

### Requirement: Local Command No-Spec Flag
The `veri local` command SHALL support `--no-spec` / `--skip-tasks` flags to bypass spec selection.

#### Scenario: Skip Spec Selection
- **WHEN** running `veri local "Fix bug" --no-spec`
- **THEN** it SHALL bypass spec selection completely
- **AND** it SHALL NOT show the interactive selection menu
- **AND** it SHALL proceed with other quality gates
