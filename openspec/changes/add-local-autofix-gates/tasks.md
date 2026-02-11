## 1. Schema & Configuration

- [x] 1.1 Add `fix_command: str | None` field to `QualityGate` in `src/veridical/config/schema.py`
- [x] 1.2 Update `.veridical.yaml.template` with `fix_command` examples (e.g., `ruff-format` gate)
- [x] 1.3 Update default config template in `src/veridical/config/defaults.py` with `fix_command` examples

## 2. Verifier Autofix Logic

- [x] 2.1 Add `autofix_enabled: bool` attribute to `Verifier` (default `True`)
- [x] 2.2 Implement `_run_autofix(gate, gate_result)` method in `Verifier` that executes `fix_command` and re-runs the gate
- [x] 2.3 Integrate autofix into `run_all()`: after collecting failed gates with `fix_command`, run autofix and update results
- [x] 2.4 Log warnings when `fix_command` exits non-zero

## 3. CLI Integration

- [x] 3.1 Add `--no-fix` flag to `veri verify` in `src/veridical/cli/verify.py`
- [x] 3.2 Set `verifier.autofix_enabled = False` when `--no-fix` is passed
- [x] 3.3 Set `verifier.autofix_enabled = False` in Jules supervisor (`veri run`) since Jules has no patch upload API

## 4. Testing

- [x] 4.1 Unit test: gate with `fix_command` succeeds after autofix
- [x] 4.2 Unit test: gate with `fix_command` still fails after autofix (fallback to normal failure)
- [x] 4.3 Unit test: `fix_command` exits non-zero (warning logged, gate failure unchanged)
- [x] 4.4 Unit test: autofix disabled — `fix_command` not executed
- [x] 4.5 Unit test: gate without `fix_command` — no autofix attempt
- [x] 4.6 Integration test: `veri verify` runs fix commands by default; `--no-fix` disables them
- [x] 4.7 Integration test: local supervisor loop skips LLM iteration when autofix resolves all failures
