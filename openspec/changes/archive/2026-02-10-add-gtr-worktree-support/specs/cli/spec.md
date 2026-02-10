## ADDED Requirements

### Requirement: gtr Worktree Flag
The `veri local` command SHALL support a `--gtr` flag to enable git worktree isolation via gtr.

#### Scenario: gtr Flag Enabled
- **WHEN** running `veri local "Fix bug" --gtr`
- **THEN** the system SHALL create a git worktree via `git gtr new` with an auto-generated branch name
- **AND** the worker command SHALL execute inside the worktree directory
- **AND** the verifier SHALL run against the worktree path

#### Scenario: gtr Flag Disabled by Default
- **WHEN** running `veri local "Fix bug"` without `--gtr`
- **AND** `local.gtr_enabled` is not set or is `false`
- **THEN** the system SHALL run in the current working directory as before
- **AND** no worktree SHALL be created

#### Scenario: gtr Flag with Config Enabled
- **WHEN** running `veri local "Fix bug"` without `--gtr`
- **AND** `local.gtr_enabled` is `true` in config
- **THEN** the system SHALL enable gtr worktree isolation
- **AND** behavior SHALL be identical to passing `--gtr`

#### Scenario: gtr Not Installed
- **WHEN** running `veri local "Fix bug" --gtr`
- **AND** `git gtr` is not available on PATH
- **THEN** the system SHALL display an error with gtr install instructions (link to https://github.com/coderabbitai/git-worktree-runner)
- **AND** it SHALL exit with code 1

#### Scenario: gtr Branch Name from Spec
- **WHEN** running `veri local` with `--gtr`
- **AND** a spec named "add-user-auth" is selected
- **THEN** the auto-generated branch name SHALL be `veri/add-user-auth`
- **AND** the branch name SHALL be displayed to the user

#### Scenario: gtr Branch Name from Task Description
- **WHEN** running `veri local "Fix login validation bug" --gtr`
- **AND** no spec is selected
- **THEN** the auto-generated branch name SHALL be derived from the task description (e.g., `veri/fix-login-validation-bug`)
- **AND** the branch name SHALL contain only lowercase letters, numbers, and hyphens

#### Scenario: gtr Merge and Cleanup on Success
- **WHEN** the local loop completes successfully with gtr enabled
- **THEN** the system SHALL attempt to merge the worktree branch back to the starting branch (the branch the user was on when `veri local` was invoked)
- **AND** if the merge succeeds, it SHALL display a message confirming the merge
- **AND** if the merge succeeds and `local.gtr_auto_cleanup` is `true`, it SHALL remove the worktree via `git gtr rm`
- **AND** if the merge succeeds and `local.gtr_auto_cleanup` is `false`, it SHALL keep the worktree intact

#### Scenario: gtr Merge Conflict on Success
- **WHEN** the local loop completes successfully with gtr enabled
- **AND** the automatic merge fails due to conflicts
- **THEN** the system SHALL abort the merge and keep the worktree intact
- **AND** it SHALL display the worktree path and branch name
- **AND** it SHALL instruct the user to merge manually (e.g., `cd <worktree-path>` or `git merge veri/<branch>`)
- **AND** it SHALL exit with code 0 (the work itself succeeded)

#### Scenario: gtr Preserved on Failure
- **WHEN** the local loop fails with gtr enabled
- **THEN** the system SHALL NOT attempt to merge the worktree branch
- **AND** it SHALL keep the worktree intact for inspection or continued work
- **AND** it SHALL display the worktree path and branch name so the user can navigate to it
