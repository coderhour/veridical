# Change: Add Parallel Quality Gate Execution

## Why
Quality gates currently run sequentially, which can significantly slow verification when running independent tools like `pytest`, `ruff`, and `mypy`. Enabling parallel execution can reduce total verification time by 50-70%.

## What Changes
- Add `parallel: bool` configuration option for quality gates
- Implement `asyncio.gather()` for parallel gate execution
- Group gates into parallel/sequential batches based on dependencies
- Preserve fail-fast behavior for required gates within parallel groups

## Impact
- Affected specs: verifier
- Affected code: `src/veridical/verifier/quality_gate.py`, `src/veridical/config/schema.py`
