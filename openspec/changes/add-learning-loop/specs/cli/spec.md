## ADDED Requirements

### Requirement: Learn Subcommand Group
The CLI SHALL provide a `learn` subcommand group for analyzing work log history and managing learned rules.

#### Scenario: Learn Analyze
- **WHEN** running `veri learn analyze`
- **THEN** it SHALL read all work log files from the configured worklog directory
- **AND** it SHALL display a pattern analysis report including: per-gate failure frequencies, stagnation patterns, and error category clusters
- **AND** it SHALL exit with code 0

#### Scenario: Learn Analyze with Insufficient Data
- **WHEN** running `veri learn analyze`
- **AND** fewer than 5 completed runs exist in the worklog directory
- **THEN** it SHALL display: "Insufficient data for pattern analysis. At least 5 completed runs are required."
- **AND** it SHALL exit with code 0

#### Scenario: Learn Apply
- **WHEN** running `veri learn apply`
- **THEN** it SHALL generate prompt improvement rules from the latest pattern analysis
- **AND** it SHALL display the proposed rules and ask for confirmation
- **AND** upon confirmation it SHALL save rules to `.veridical/learned_rules.yaml`

#### Scenario: Learn Apply to AGENTS.md
- **WHEN** running `veri learn apply --agents-md`
- **THEN** it SHALL append learned rules to the project's AGENTS.md under a `# Learned Rules` section
- **AND** it SHALL display a diff preview before writing
- **AND** it SHALL require explicit confirmation before modifying AGENTS.md

#### Scenario: Learn Predict
- **WHEN** running `veri learn predict "Fix the login validation bug"`
- **THEN** it SHALL compare the task description to historical tasks
- **AND** it SHALL display: estimated iteration count, confidence level, and similar historical tasks

#### Scenario: Learn Rules List
- **WHEN** running `veri learn rules`
- **THEN** it SHALL display all learned rules in a Rich table with columns: ID, Rule, Confidence, Created, Applied Count, Success Rate

#### Scenario: Learn Rules Prune
- **WHEN** running `veri learn rules --prune`
- **THEN** it SHALL remove stale rules (older than 90 days with success rate below 50%)
- **AND** it SHALL display the count of pruned rules

#### Scenario: Learn No Worklog Directory
- **WHEN** running `veri learn analyze`
- **AND** the configured worklog directory does not exist
- **THEN** it SHALL display: "No work logs found. Run `veri run` or `veri local` first to generate work logs."
- **AND** it SHALL exit with code 1
