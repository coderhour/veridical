## ADDED Requirements

### Requirement: Learning Configuration
The system SHALL support a `learning` configuration section for work log analysis and prompt optimization settings.

#### Scenario: Learning Config Section
- **WHEN** accessing `config.learning`
- **THEN** it SHALL contain `history_depth: int` (default: `50`, maximum number of past runs to analyze)
- **AND** it SHALL contain `auto_inject_rules: bool` (default: `False`, whether to automatically inject learned rules into dispatch prompts)
- **AND** it SHALL contain `rules_file: str` (default: `.veridical/learned_rules.yaml`, path to the learned rules file)
- **AND** it SHALL contain `min_runs_for_analysis: int` (default: `5`, minimum completed runs before pattern analysis is available)

#### Scenario: Learning Config Defaults
- **WHEN** no `learning` section is specified in `.veridical.yaml`
- **THEN** the system SHALL use default values
- **AND** `veri learn` commands SHALL function with defaults

#### Scenario: Learning Config in Template
- **WHEN** generating a config template
- **THEN** it SHALL include a commented `learning` section with `history_depth`, `auto_inject_rules`, `rules_file`, and `min_runs_for_analysis` fields
