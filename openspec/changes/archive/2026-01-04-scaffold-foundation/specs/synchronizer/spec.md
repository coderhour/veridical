# Synchronizer Specification Delta

## ADDED Requirements

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

The system SHALL create isolated branches for each iteration to prevent pollution of main.

#### Scenario: Create Iteration Branch

WHEN calling `synchronizer.create_iteration_branch(iteration: int)`
THEN it SHALL create a new branch named `veridical/iter-{iteration}`
AND it SHALL checkout that branch
AND it SHALL return the branch name

#### Scenario: Branch Already Exists

WHEN a branch with the same name already exists
THEN it SHALL delete the existing branch first
AND it SHALL create the new branch

### Requirement: Patch Application

The system SHALL apply patches received from Jules to the local repository.

#### Scenario: Apply Patch Successfully

WHEN calling `synchronizer.apply_patch(patch_data: str)`
AND the patch applies cleanly
THEN it SHALL return `PatchResult(success=True, files_changed=[...])`

#### Scenario: Patch Application Failure

WHEN calling `synchronizer.apply_patch(patch_data: str)`
AND the patch cannot be applied cleanly
THEN it SHALL return `PatchResult(success=False, error="...")`
AND it SHALL NOT leave the repository in a dirty state

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
