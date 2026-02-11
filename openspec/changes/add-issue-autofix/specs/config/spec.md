## ADDED Requirements

### Requirement: Heal Configuration
The system SHALL support a `heal` configuration section for the GitHub issue auto-fix pipeline.

#### Scenario: Heal Config Section
- **WHEN** accessing `config.heal`
- **THEN** it SHALL contain `watch_labels: list[str]` (default: `["veridical", "auto-fix"]`)
- **AND** it SHALL contain `watch_interval: int` (default: `60`, polling interval in seconds for watch mode)
- **AND** it SHALL contain `auto_pr: bool` (default: `True`, whether to auto-create PRs on success)
- **AND** it SHALL contain `comment_on_failure: bool` (default: `True`, whether to comment on issues when fix fails)
- **AND** it SHALL contain `auto_spec_threshold: str` (default: `"high"`, complexity level at which auto-spec is triggered)

#### Scenario: Heal Config Defaults
- **WHEN** no `heal` section is specified in `.veridical.yaml`
- **THEN** the system SHALL use default values
- **AND** the heal pipeline SHALL function with defaults when invoked

#### Scenario: GitHub Token Handling
- **WHEN** the heal pipeline is invoked
- **THEN** it SHALL read the GitHub token from `GITHUB_TOKEN` environment variable
- **AND** it SHALL NOT accept tokens from config files
- **AND** it SHALL raise `ConfigurationError` if the token is missing
