# Change: Add Learning Loop and Prompt Optimization (`veri learn`)

## Why
Veridical already produces detailed work logs and run reports, but this data is discarded after each run. Anthropic's key insight with Claude Code is that `CLAUDE.md` accumulates learnings ("every mistake becomes a rule"), and Factory.ai attributes its 84.8% SWE-bench solve rate partly to learning from past runs. Veridical should close the learning loop by analyzing historical work logs to identify recurring failure patterns, optimize prompts, and predict task difficulty — getting smarter with every run.

## What Changes
- Add a new `veridical.learning` module with `PatternAnalyzer`, `PromptOptimizer`, and `DifficultyEstimator` classes
- Add a new CLI command `veri learn` with `--analyze`, `--apply`, and `--predict` subcommands
- `PatternAnalyzer` identifies recurring gate failures, stagnation patterns, and common error categories across work log history
- `PromptOptimizer` generates prompt improvement rules (e.g., "always check imports") based on failure patterns
- `DifficultyEstimator` predicts iteration count for new tasks based on historical similarity
- Support auto-evolving AGENTS.md with learned rules (with human approval gate)
- Add `LearningConfig` section to `.veridical.yaml` for history depth, auto-apply settings

## Impact
- Affected specs: `cli`, `config`
- New capability: `learning` (new spec)
- Affected code: `src/veridical/learning/` (new), `src/veridical/cli/learn.py` (new), `src/veridical/config/schema.py`
