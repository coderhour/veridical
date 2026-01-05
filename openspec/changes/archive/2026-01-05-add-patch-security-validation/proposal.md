# Change: Add Patch Security Validation

## Why
The `PatchApplier` applies patches without inspection. Jules could theoretically modify `.github/workflows/`, `AGENTS.md`, or other sensitive files. The project documentation mentions "Diff Inspection" and "Zombie Defense" but these aren't implemented.

## What Changes
- Add `ScopeValidator` class for patch file inspection
- Implement allowlist/denylist configuration for file patterns
- Add security gate that rejects patches touching sensitive files
- Log all file changes for audit trail

## Impact
- Affected specs: synchronizer
- Affected code: `src/veridical/synchronizer/patch.py`, `src/veridical/synchronizer/validator.py`, `src/veridical/config/schema.py`
