## 1. Coverage Analysis Module
- [x] 1.1 Create `src/veridical/verifier/test_coverage.py` with `DiffCoverageAnalyzer` class
- [x] 1.2 Implement diff parsing to extract new/changed functions and their file:line locations
- [x] 1.3 Implement coverage report parsing (support `pytest-cov` JSON output format)
- [x] 1.4 Implement uncovered-function detection by cross-referencing diff with coverage data
- [x] 1.5 Implement structured feedback output listing uncovered functions with file:line references

## 2. Gate Type Integration
- [x] 2.1 Add `test_generation` to the `QualityGate.type` literal in `src/veridical/config/schema.py`
- [x] 2.2 Add `coverage_command`, `coverage_threshold`, and `coverage_format` fields to `QualityGate`
- [x] 2.3 Add `test_generation` dispatch case in `Verifier._run_gate_logic()` in `quality_gate.py`
- [x] 2.4 Implement the gate runner that executes coverage command, parses output, and checks threshold

## 3. Configuration
- [x] 3.1 Add example `test_generation` gate to `.veridical.yaml.template` (commented out)
- [x] 3.2 Document gate configuration options in template comments

## 4. Tests
- [x] 4.1 Unit tests for `DiffCoverageAnalyzer` with sample diffs and coverage reports
- [x] 4.2 Unit tests for gate type validation (schema accepts `test_generation`)
- [x] 4.3 Integration test: `test_generation` gate fails when new function lacks coverage
- [x] 4.4 Integration test: `test_generation` gate passes when all new functions are covered
- [x] 4.5 Integration test: structured feedback contains correct file:line references
