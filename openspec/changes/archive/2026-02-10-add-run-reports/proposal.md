# Change: Add Structured Run Reports and Observability

## Why
Veridical already captures raw iteration data in work logs (`worklog/YYYY-MM-DD/iterations.jsonl`), but there is no way to review, analyze, or learn from past runs. For an autonomous system, observability is essential — operators need to understand how many iterations a task took, which gates failed most often, what feedback was sent, and whether the system is improving over time. Without structured reports, tuning verification rules and prompts is guesswork. A `veri report` command and structured report generation close the feedback loop for the human operator.

## What Changes
- Add a `veri report` CLI command that summarizes a completed run from work log data
- Implement a `ReportGenerator` that parses work log JSONL files and produces structured summaries
- Support multiple output formats: terminal (Rich tables), JSON, and single-file HTML
- Include per-iteration breakdown: duration, gates run, gates failed, feedback sent, worker response
- Include aggregate metrics: total duration, success rate, most-failed gates, average iterations to success
- Add cost tracking fields to work log entries (API calls, estimated token usage, VM time)
- Add pattern detection: identify gates that consistently fail on first iteration

## Impact
- Affected specs: `cli`, `config`
- Affected code: `src/veridical/cli/`, `src/veridical/report/` (new module), `src/veridical/worklog/`
- No breaking changes — extends existing work log infrastructure
