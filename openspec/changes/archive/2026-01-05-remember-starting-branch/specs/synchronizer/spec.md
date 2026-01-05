# synchronizer Specification Delta

## MODIFIED Requirements

### Requirement: Branch Cleanup

The system SHALL clean up iteration branches after use.

#### Scenario: Merge Successful Iteration to Work Branch

GIVEN a successful verification on iteration branch `veridical/iter-3`
AND `auto_create_work_branch` is enabled
AND the work branch is `feat/add-user-auth`
WHEN calling `synchronizer.merge_to_main(branch_name: str)`
THEN it SHALL checkout the work branch (`feat/add-user-auth`)
AND it SHALL merge the iteration branch with a merge commit
AND it SHALL delete the iteration branch
AND it SHALL return to the starting branch

#### Scenario: Merge with Target Override

GIVEN a successful verification on iteration branch `veridical/iter-3`
AND the user specified `--target-branch custom-branch`
WHEN calling `synchronizer.merge_to_main(branch_name: str)`
THEN it SHALL checkout `custom-branch` (the overridden target)
AND it SHALL merge the iteration branch with a merge commit
AND it SHALL delete the iteration branch

#### Scenario: Legacy Merge to Base Branch

GIVEN a successful verification on iteration branch `veridical/iter-3`
AND `auto_create_work_branch` is disabled
WHEN calling `synchronizer.merge_to_main(branch_name: str)`
THEN it SHALL checkout the configured `base_branch`
AND it SHALL merge the iteration branch with a merge commit
AND it SHALL delete the iteration branch

## ADDED Requirements

### Requirement: Starting Branch Detection

The `Synchronizer` SHALL capture and remember the current branch when initialized.

#### Scenario: Capture Current Branch

GIVEN the user is on branch `feature/my-work`
WHEN Veridical initializes the `Synchronizer`
THEN it SHALL store `feature/my-work` as the starting branch
AND it SHALL return to this branch after completion

#### Scenario: Detached HEAD Fallback

GIVEN the user is in a detached HEAD state
WHEN Veridical initializes the `Synchronizer`
THEN it SHALL fall back to the configured `base_branch`
AND it SHALL log a warning about the detached HEAD state

### Requirement: Work Branch Creation

The `Synchronizer` SHALL create a dedicated work branch when `auto_create_work_branch` is enabled.

#### Scenario: Create Work Branch from Spec Name

GIVEN `auto_create_work_branch` is `true`
AND the spec name is "Add User Authentication"
WHEN Veridical starts a verification loop
THEN it SHALL create branch `feat/add-user-authentication` from `base_branch`
AND all successful iteration merges SHALL target this work branch

#### Scenario: Create Work Branch from Task Description

GIVEN `auto_create_work_branch` is `true`
AND no spec name is detected
AND the task description is "Fix login validation bug"
WHEN Veridical starts a verification loop
THEN it SHALL create branch `fix/fix-login-validation-bug` from `base_branch`

#### Scenario: Work Branch Already Exists

GIVEN `auto_create_work_branch` is `true`
AND branch `feat/add-user-auth` already exists
WHEN Veridical starts a verification loop
THEN it SHALL checkout the existing branch
AND it SHALL NOT recreate or reset the branch

### Requirement: Branch Name Sanitization

The `Synchronizer` SHALL sanitize branch names to contain only valid characters.

#### Scenario: Sanitize Special Characters

GIVEN a spec name "Add User's Auth (v2.0)"
WHEN generating the work branch name
THEN it SHALL produce `feat/add-users-auth-v20`
AND the name SHALL contain only lowercase letters, numbers, and hyphens

#### Scenario: Sanitize Spaces and Underscores

GIVEN a task description "Fix_login bug"
WHEN generating the work branch name
THEN it SHALL produce `fix/fix-login-bug`

#### Scenario: Handle Empty or Invalid Names

GIVEN an empty or invalid name that sanitizes to empty string
WHEN generating the work branch name
THEN it SHALL fall back to `feat/veridical-work` or `fix/veridical-work`
