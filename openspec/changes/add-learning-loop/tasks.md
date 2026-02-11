## 1. Learning Module
- [ ] 1.1 Create `src/veridical/learning/__init__.py` with module exports
- [ ] 1.2 Implement `PatternAnalyzer` in `src/veridical/learning/patterns.py` (analyze work log history for recurring gate failures, stagnation patterns, error categories)
- [ ] 1.3 Implement `PromptOptimizer` in `src/veridical/learning/optimizer.py` (generate prompt improvement rules from failure patterns)
- [ ] 1.4 Implement `DifficultyEstimator` in `src/veridical/learning/estimator.py` (predict iteration count based on historical similarity)
- [ ] 1.5 Implement `RuleManager` in `src/veridical/learning/rules.py` (manage learned rules, apply to AGENTS.md with human approval)

## 2. Configuration
- [ ] 2.1 Add `LearningConfig` model to `src/veridical/config/schema.py` with `history_depth`, `auto_apply`, `rules_file` fields
- [ ] 2.2 Add `learning: LearningConfig` field to `VeridicalConfig`
- [ ] 2.3 Add `learning` section to `.veridical.yaml.template` with documented options

## 3. CLI Commands
- [ ] 3.1 Create `src/veridical/cli/learn.py` with `veri learn` Typer command group
- [ ] 3.2 Implement `veri learn analyze` subcommand (display pattern insights from work log history)
- [ ] 3.3 Implement `veri learn apply` subcommand (apply learned rules to AGENTS.md or prompt templates)
- [ ] 3.4 Implement `veri learn predict` subcommand (estimate difficulty and iteration count for a given task)
- [ ] 3.5 Implement `veri learn rules` subcommand (list, add, remove learned rules)
- [ ] 3.6 Register `learn` command group in main CLI app

## 4. Supervisor Integration
- [ ] 4.1 In `Supervisor.run()`, optionally load learned rules and inject into dispatch prompt
- [ ] 4.2 In `LocalSupervisor.run()`, optionally load learned rules and inject into worker environment
- [ ] 4.3 After each run, optionally record new patterns discovered during the run

## 5. Tests
- [ ] 5.1 Unit tests for `PatternAnalyzer` with sample work log JSONL files
- [ ] 5.2 Unit tests for `PromptOptimizer` rule generation from sample patterns
- [ ] 5.3 Unit tests for `DifficultyEstimator` prediction accuracy with historical data
- [ ] 5.4 Unit tests for `RuleManager` CRUD operations on rules file
- [ ] 5.5 Integration test: `veri learn analyze` output with sample work log directory
- [ ] 5.6 Integration test: learned rules are injected into supervisor dispatch prompt
