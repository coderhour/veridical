## ADDED Requirements

### Requirement: Learning Module Structure
The system SHALL provide a `veridical.learning` module for analyzing work log history and generating actionable insights to improve future runs.

#### Scenario: Module Import
- **WHEN** importing `from veridical.learning import PatternAnalyzer, PromptOptimizer, DifficultyEstimator`
- **THEN** the import SHALL succeed without errors

### Requirement: Pattern Analyzer
The system SHALL provide a `PatternAnalyzer` class that mines work log history for recurring failure patterns.

#### Scenario: Gate Failure Frequency
- **WHEN** calling `analyzer.analyze(worklog_dir)` with a directory containing work log JSONL files
- **THEN** it SHALL return a `PatternReport` containing per-gate failure frequencies (e.g., "ruff failed on 80% of first iterations")

#### Scenario: Stagnation Pattern Detection
- **WHEN** analyzing work logs
- **AND** multiple runs exhibit stagnation (identical diff hashes across iterations)
- **THEN** the `PatternReport` SHALL identify the stagnation pattern with the affected task descriptions

#### Scenario: Error Category Clustering
- **WHEN** analyzing work logs
- **THEN** it SHALL group error contexts into categories (e.g., "import errors", "type errors", "test failures")
- **AND** each category SHALL include frequency count and example error excerpts

#### Scenario: Insufficient Data
- **WHEN** calling `analyzer.analyze(worklog_dir)`
- **AND** fewer than 5 completed runs exist in the work log directory
- **THEN** it SHALL return a `PatternReport` with `sufficient_data=False`
- **AND** it SHALL include a message: "Insufficient data for pattern analysis. At least 5 completed runs are required."

### Requirement: Prompt Optimizer
The system SHALL provide a `PromptOptimizer` class that generates prompt improvement rules from failure patterns.

#### Scenario: Rule Generation from Patterns
- **WHEN** calling `optimizer.generate_rules(pattern_report)`
- **AND** the pattern report shows "import errors" occur in 70% of first iterations
- **THEN** it SHALL generate a rule: "Always verify import statements are correct before submitting code"
- **AND** the rule SHALL include `trigger_pattern`, `rule_text`, `confidence_score`, and `created_at`

#### Scenario: Rule Deduplication
- **WHEN** generating rules
- **AND** a semantically similar rule already exists in the rules file
- **THEN** it SHALL update the existing rule's confidence score instead of creating a duplicate

#### Scenario: Rule Format
- **WHEN** a rule is generated
- **THEN** it SHALL be a `LearnedRule` object with fields: `id`, `trigger_pattern`, `rule_text`, `confidence_score` (0.0-1.0), `created_at`, `applied_count`, and `success_rate`

### Requirement: Difficulty Estimator
The system SHALL provide a `DifficultyEstimator` class that predicts iteration count for new tasks based on historical similarity.

#### Scenario: Iteration Prediction
- **WHEN** calling `estimator.predict(task_description, worklog_dir)`
- **THEN** it SHALL compare the task description to historical tasks using keyword similarity
- **AND** it SHALL return a `DifficultyEstimate` with `predicted_iterations`, `confidence`, and `similar_tasks` (list of matching historical tasks)

#### Scenario: No Similar Tasks Found
- **WHEN** calling `estimator.predict(task_description, worklog_dir)`
- **AND** no historically similar tasks are found
- **THEN** it SHALL return a `DifficultyEstimate` with `confidence="low"` and `predicted_iterations` set to the configured `max_iterations / 2`

### Requirement: Rule Manager
The system SHALL provide a `RuleManager` class that persists and manages learned rules in a YAML file.

#### Scenario: Load Rules
- **WHEN** calling `manager.load()`
- **THEN** it SHALL read rules from `.veridical/learned_rules.yaml`
- **AND** it SHALL return a list of `LearnedRule` objects

#### Scenario: Save Rules
- **WHEN** calling `manager.save(rules)`
- **THEN** it SHALL write rules to `.veridical/learned_rules.yaml` in YAML format
- **AND** the file SHALL be human-readable and versionable

#### Scenario: Apply Rules to AGENTS.md
- **WHEN** calling `manager.apply_to_agents_md(rules, agents_md_path)`
- **THEN** it SHALL append a `# Learned Rules` section to AGENTS.md with the rule texts
- **AND** it SHALL NOT modify existing AGENTS.md content above the `# Learned Rules` section
- **AND** it SHALL require explicit confirmation before writing (human approval gate)

#### Scenario: Prune Stale Rules
- **WHEN** calling `manager.prune(max_age_days=90)`
- **THEN** it SHALL remove rules older than the specified age that have a `success_rate` below 0.5
- **AND** it SHALL return the count of pruned rules
