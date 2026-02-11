## Context
Veridical produces detailed work logs (JSONL) for every run, containing iteration count, gate results, error context, prompts sent, and timing data. This data is currently only used for post-run reporting. Closing the learning loop means mining this history to improve future runs — identifying failure patterns, optimizing prompts, and predicting difficulty.

## Goals / Non-Goals
- Goals:
  - Analyze work log history to surface recurring failure patterns (e.g., "ruff fails on 80% of first iterations")
  - Generate actionable prompt improvement rules from patterns
  - Predict iteration count and difficulty for new tasks based on historical similarity
  - Support auto-evolving AGENTS.md with learned rules (human-approved)
  - Provide CLI interface for reviewing and managing learned insights
- Non-Goals:
  - Fine-tuning LLMs on work log data (far too complex for v1)
  - Real-time learning during a single run (learning happens between runs)
  - Automatic prompt modification without human review

## Decisions
- **Work log JSONL as the data source**: Already structured, already persisted. No new data collection needed.
- **Rules stored as YAML**: Simple, human-readable, versionable. Stored in `.veridical/learned_rules.yaml`.
- **Similarity estimation uses keyword overlap**: Simple TF-IDF-like approach for matching new tasks to historical tasks. LLM-based similarity is a future enhancement.
- **Human approval gate for AGENTS.md changes**: `veri learn apply` shows proposed changes and requires confirmation before modifying AGENTS.md.
- Alternatives considered:
  - SQLite database for analytics → YAML/JSONL is simpler and doesn't introduce a new dependency.
  - Automatic rule injection (no human approval) → Too risky; bad rules could degrade performance.

## Risks / Trade-offs
- **Pattern quality depends on log volume** → Minimum 5 runs before patterns are surfaced. Display a message if insufficient data.
- **Keyword-based similarity is approximate** → Acceptable for v1. LLM-based matching can be added later.
- **Stale rules** → Rules should include a `created_at` timestamp and can be pruned via `veri learn rules --prune`.

## Open Questions
- Should rules be project-specific (`.veridical/`) or global (`~/.veridical/`)?
- Should `veri learn predict` require a local LLM, or can it work with keyword heuristics alone?
- How should rules be prioritized when there are many? (Most-frequently-triggered first?)
