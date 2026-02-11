# Change: Add Local Autofix for Tool-Fixable Quality Gates

## Why
Quality gates like `ruff format --check` detect issues that can be fixed deterministically by running a tool command (e.g., `ruff format src/`). Today, these failures are fed back to the LLM worker, wasting an iteration on something a local tool can resolve instantly. For `veri local`, we can run the fix command directly. Jules does not support patch upload, so this feature is scoped to `veri local` (and `veri verify --fix`) only.

## What Changes
- Add an optional `fix_command` field to the `QualityGate` config schema
- When a gate fails and has a `fix_command`, the local supervisor automatically runs the fix command before feeding errors to the LLM worker
- Add a `--fix` flag to `veri verify` to run fix commands for failed gates
- Re-run the fixed gates to confirm the fix succeeded; if it still fails, treat it as a normal failure for the LLM worker
- Jules mode (`veri run`) ignores `fix_command` entirely (remote VM, no local fix possible)

## Impact
- Affected specs: `verifier`, `config`
- Affected code: `src/veridical/verifier/quality_gate.py`, `src/veridical/config/schema.py`, `src/veridical/local/supervisor.py`, `src/veridical/cli/verify.py`
