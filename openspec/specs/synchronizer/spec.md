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

#### Scenario: Delete Iteration Branch

WHEN calling `synchronizer.cleanup_branch(branch_name: str)`
THEN it SHALL checkout `main` (or configured base branch)
AND it SHALL delete the specified branch

#### Scenario: Merge Successful Iteration

WHEN calling `synchronizer.merge_to_main(branch_name: str)`
THEN it SHALL checkout `main`
AND it SHALL merge the specified branch with a merge commit
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

