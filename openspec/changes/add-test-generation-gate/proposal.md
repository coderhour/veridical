# Change: Add Test Generation Quality Gate

## Why
Autonomous agents frequently produce code changes without adequate test coverage. Research (arxiv.org/abs/2601.03556) shows agent PRs include far fewer tests than human PRs. Veridical currently runs existing tests but does not enforce that new/changed code has corresponding new tests. A `test_generation` gate closes this gap by failing verification when the agent's diff introduces untested code, forcing the agent to write tests before the loop can succeed.

## What Changes
- Add a new quality gate type `test_generation` that analyzes the current diff for untested new/changed functions
- Add `src/veridical/verifier/test_coverage.py` with diff-aware coverage analysis logic
- Extend `QualityGate` schema to accept `test_generation` type with configurable coverage command and threshold
- Extend `Verifier._run_gate_logic()` to dispatch to the new gate type
- Produce structured feedback listing specific uncovered functions with file:line references

## Impact
- Affected specs: `verifier`, `config`
- Affected code: `src/veridical/verifier/test_coverage.py` (new), `src/veridical/verifier/quality_gate.py`, `src/veridical/config/schema.py`
