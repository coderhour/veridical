# synchronizer Specification

## Purpose
TBD - created by archiving change scaffold-foundation. Update Purpose after archive.
## Requirements
### Requirement: Synchronizer Module Structure

The system SHALL provide a `veridical.synchronizer` module for git operations and patch management.

#### Scenario: Module Import

WHEN importing `from veridical.synchronizer import Synchronizer`
THEN the import SHALL succeed without errors

#### Scenario: Synchronizer Interface

WHEN instantiating the Synchronizer class
THEN it SHALL accept a `repo_path` parameter of type `Path`
AND it SHALL accept a `config` parameter of type `VeridicalConfig`

### Requirement: Isolation Branch Management
The `Synchronizer` SHALL manage iteration isolation.

#### Scenario: Verify Isolation
- **GIVEN** a running loop at iteration 1
- **WHEN** applying a patch
- **THEN** it must create and checkout `veridical/iter-1`
- **AND** apply the patch there
- **AND** leave `main` branch untouched

### Requirement: Patch Application
The `Synchronizer` SHALL apply remote diffs cleanly.

#### Scenario: Clean Patch
- **GIVEN** a valid unified diff from Jules
- **WHEN** `apply_patch` is called
- **THEN** it must update local files
- **AND** return `PatchResult.APPLIED`

#### Scenario: Patch Conflict
- **GIVEN** a patch that conflicts with local changes
- **WHEN** `apply_patch` is called
- **THEN** it must return `PatchResult.CONFLICT`
- **AND** not modify the file system (atomic failure)

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

### Requirement: Diff Inspection

The system SHALL provide methods to inspect diffs for scope validation.

#### Scenario: Get Changed Files

WHEN calling `synchronizer.get_changed_files()`
THEN it SHALL return a list of file paths that have been modified
AND it SHALL include the type of change (added, modified, deleted)

#### Scenario: Diff Hash Calculation

WHEN calling `synchronizer.get_diff_hash()`
THEN it SHALL return a deterministic hash of the current diff
AND repeated calls with the same diff SHALL return the same hash

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

### Requirement: Patch Scope Validation
The system SHALL validate patches against configurable scope rules before application.

#### Scenario: Denylist Violation in Strict Mode
- **WHEN** a patch modifies a file matching the denylist (e.g., `.github/workflows/`)
- **AND** `strict_mode` is `true`
- **THEN** the patch SHALL be rejected
- **AND** `PatchResult.status` SHALL be `SCOPE_VIOLATION`
- **AND** the error SHALL list all violated files

#### Scenario: Denylist Violation in Warning Mode
- **WHEN** a patch modifies a file matching the denylist
- **AND** `strict_mode` is `false`
- **THEN** the patch SHALL be applied
- **AND** a warning SHALL be logged listing violated files

#### Scenario: Allowlist Override
- **WHEN** a file matches both allowlist and denylist patterns
- **THEN** the allowlist SHALL take precedence
- **AND** the file SHALL be allowed

#### Scenario: Clean Patch Validation
- **WHEN** a patch modifies only files not matching the denylist
- **THEN** validation SHALL pass
- **AND** the patch SHALL proceed to application

### Requirement: Security Audit Logging
The system SHALL log all patch operations for security audit.

#### Scenario: Patch Application Logged
- **WHEN** a patch is successfully applied
- **THEN** the system SHALL log all modified file paths
- **AND** the log entry SHALL include session ID and iteration number

#### Scenario: Rejected Patch Logged
- **WHEN** a patch is rejected due to scope violation
- **THEN** the system SHALL log the rejection at WARNING level
- **AND** the log SHALL include violated patterns and file paths
- **AND** the log SHALL include session ID for traceability

### Requirement: Default Security Denylist
The system SHALL provide a default denylist of sensitive file patterns.

#### Scenario: Default Denylist Contents
- **WHEN** no custom denylist is configured
- **THEN** the default denylist SHALL include:
  - `.github/**`
  - `.gitlab-ci.yml`
  - `AGENTS.md`
  - `*.env`
  - `.veridical.yaml`
  - `Dockerfile`
  - `docker-compose*.yml`

