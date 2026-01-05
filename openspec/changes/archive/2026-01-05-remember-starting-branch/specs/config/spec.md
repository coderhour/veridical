# config Specification Delta

## MODIFIED Requirements

### Requirement: Configuration Schema

The system SHALL define a `VeridicalConfig` Pydantic model.

#### Scenario: Git Config Section

WHEN accessing `config.git`
THEN it SHALL contain `base_branch: str` (default: `main`)
AND it SHALL contain `branch_prefix: str` (default: `veridical/iter-`)
AND it SHALL contain `auto_cleanup: bool` (default: `true`)
AND it SHALL contain `auto_create_work_branch: bool` (default: `true`)

> **Delta**: Added `auto_create_work_branch` field with `true` as default.

## ADDED Requirements

### Requirement: Auto Create Work Branch Configuration

The system SHALL support configuration for automatic work branch creation.

#### Scenario: Default Enabled

WHEN `git.auto_create_work_branch` is not specified in config
THEN it SHALL default to `true`
AND Veridical SHALL create a work branch for each run

#### Scenario: Explicitly Disabled

WHEN `git.auto_create_work_branch` is set to `false`
THEN Veridical SHALL use legacy behavior (merge to `base_branch`)
AND no work branch SHALL be created

#### Scenario: Environment Variable Override

WHEN environment variable `VERIDICAL_GIT__AUTO_CREATE_WORK_BRANCH` is set to `false`
THEN it SHALL override any file-based configuration
AND Veridical SHALL use legacy merge behavior
