## 1. Learning Module
- [x] 1.1 Create `src/veridical/learning/__init__.py` with module exports
- [x] 1.2 Implement `PatternAnalyzer` in `src/veridical/learning/patterns.py` (analyze work log history for recurring gate failures, stagnation patterns, error categories)
- [x] 1.3 Implement `PromptOptimizer` in `src/veridical/learning/optimizer.py` (generate prompt improvement rules from failure patterns)
- [x] 1.4 Implement `DifficultyEstimator` in `src/veridical/learning/estimator.py` (predict iteration count based on historical similarity)
- [x] 1.5 Implement `RuleManager` in `src/veridical/learning/rules.py` (manage learned rules, apply to AGENTS.md with human approval)

## 2. Configuration
- [x] 2.1 Add `LearningConfig` model to `src/veridical/config/schema.py` with `history_depth`, `auto_apply`, `rules_file` fields
- [x] 2.2 Add `learning: LearningConfig` field to `VeridicalConfig`
- [x] 2.3 Add `learning` section to `.veridical.yaml.template` with documented options

## 3. CLI Commands
- [x] 3.1 Create `src/veridical/cli/learn.py` with `veri learn` Typer command group
- [x] 3.2 Implement `veri learn analyze` subcommand (display pattern insights from work log history)
- [x] 3.3 Implement `veri learn apply` subcommand (apply learned rules to AGENTS.md or prompt templates)
- [x] 3.4 Implement `veri learn predict` subcommand (estimate difficulty and iteration count for a given task)
- [x] 3.5 Implement `veri learn rules` subcommand (list, add, remove learned rules)
- [x] 3.6 Register `learn` command group in main CLI app

## 4. Supervisor Integration
- [x] 4.1 In `Supervisor.run()`, optionally load learned rules and inject into dispatch prompt
- [x] 4.2 In `LocalSupervisor.run()`, optionally load learned rules and inject into worker environment
- [x] 4.3 After each run, optionally record new patterns discovered during the run

## 5. Tests
- [x] 5.1 Unit tests for `PatternAnalyzer` with sample work log JSONL files
- [x] 5.2 Unit tests for `PromptOptimizer` rule generation from sample patterns
- [x] 5.3 Unit tests for `DifficultyEstimator` prediction accuracy with historical data
- [x] 5.4 Unit tests for `RuleManager` CRUD operations on rules file
- [x] 5.5 Integration test: `veri learn analyze` output with sample work log directory
- [x] 5.6 Integration test: learned rules are injected into supervisor dispatch prompt
