## ADDED Requirements

### Requirement: gtr Worktree Configuration
The system SHALL support configuration fields for gtr worktree integration in the `local` config section.

#### Scenario: gtr Enabled Field
- **WHEN** accessing `config.local`
- **THEN** it SHALL contain `gtr_enabled: bool` (default: `False`)
- **AND** when `true`, the local supervisor SHALL create a git worktree for each run

#### Scenario: gtr Auto-Cleanup Field
- **WHEN** accessing `config.local`
- **THEN** it SHALL contain `gtr_auto_cleanup: bool` (default: `True`)
- **AND** when `true`, the worktree SHALL be removed after a successful run
- **AND** when `false`, the worktree SHALL be preserved after completion regardless of outcome

#### Scenario: Environment Variable Override for gtr
- **WHEN** environment variable `VERIDICAL_LOCAL__GTR_ENABLED` is set to `true`
- **THEN** it SHALL override the file-based `local.gtr_enabled` configuration
- **AND** gtr worktree isolation SHALL be enabled
