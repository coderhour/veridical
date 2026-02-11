# Change: Add Root-Cause Localization (`veri diagnose`)

## Why
When Veridical sends error context back to the worker, it sends raw or compressed log output. The agent must figure out where the bug is, which wastes iterations and cost. SWE-agent's research shows that fault localization accounts for >50% of successful resolution. By pinpointing exact files, functions, and lines before dispatching, Veridical can dramatically improve first-iteration success rates and reduce cost. This also powers smarter feedback: instead of "pytest failed", the feedback becomes "test_login failed because validate() at src/auth.py:87 returns None when password is empty".

## What Changes
- Add a new `veridical.diagnose` module with `StackTraceParser`, `CallGraphAnalyzer`, `BlameCorrelator`, and `Localizer` classes
- Add a new CLI command `veri diagnose` for standalone root-cause analysis
- Integrate localization into `FeedbackGenerator` to enrich error context with file:line references
- Integrate localization into the supervisor dispatch step to pre-localize before sending tasks to workers

## Impact
- Affected specs: `cli`, `verifier` (feedback enrichment)
- New capability: `diagnose` (new spec)
- Affected code: `src/veridical/diagnose/` (new), `src/veridical/cli/diagnose.py` (new), `src/veridical/verifier/feedback.py`
