# Synchronizer Specification

## MODIFIED Requirements

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
