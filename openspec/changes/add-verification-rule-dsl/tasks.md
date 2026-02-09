## 1. Assertion Gate Type
- [ ] 1.1 Implement `AssertionGateRunner` that checks file existence, content patterns, and schema validation
- [ ] 1.2 Support `assert_file_exists` with glob patterns
- [ ] 1.3 Support `assert_content_matches` with regex patterns against file contents
- [ ] 1.4 Support `assert_json_schema` for validating JSON/YAML files against a schema
- [ ] 1.5 Add unit tests for all assertion gate variants

## 2. Diff Scope Gate Type
- [ ] 2.1 Implement `DiffScopeGateRunner` that checks modified files against allowed glob patterns
- [ ] 2.2 Integrate with git diff to detect which files were modified in the current iteration
- [ ] 2.3 Fail if any modified file does not match the allowed patterns
- [ ] 2.4 Add unit tests for diff scope gate

## 3. Conditional Gate Modifier
- [ ] 3.1 Add `when_files_changed` field to `QualityGate` config model
- [ ] 3.2 Implement condition evaluation: skip gate if no files matching the pattern were modified
- [ ] 3.3 Log skipped gates with reason
- [ ] 3.4 Add unit tests for conditional gate execution

## 4. Composite Gate Type
- [ ] 4.1 Implement `CompositeGateRunner` with `all_of` (AND) and `any_of` (OR) sub-gate logic
- [ ] 4.2 Support nesting composite gates (composite containing composites)
- [ ] 4.3 Add unit tests for composite gate combinations

## 5. Warning and Exit Code Features
- [ ] 5.1 Add `warn_only: bool` field to `QualityGate` config model
- [ ] 5.2 Implement warning behavior: gate failure logged as warning, does not block loop
- [ ] 5.3 Add `exit_code_map` field: mapping of exit codes to `pass`, `warn`, or `fail`
- [ ] 5.4 Update `GateResult` model to include `severity` field (pass/warn/fail)
- [ ] 5.5 Add unit tests for warn_only and exit_code_map

## 6. Configuration Schema Updates
- [ ] 6.1 Extend `QualityGate` Pydantic model with new fields and gate types
- [ ] 6.2 Add validation for new gate type configurations
- [ ] 6.3 Update `.veridical.yaml.template` with examples of new gate types
- [ ] 6.4 Ensure backward compatibility: existing `command` gates work unchanged

## 7. Verifier Integration
- [ ] 7.1 Update `Verifier.run_all()` to dispatch to correct runner based on gate type
- [ ] 7.2 Update `VerificationResult` to include warning-level results
- [ ] 7.3 Update feedback generation to distinguish warnings from failures

## 8. Documentation
- [ ] 8.1 Update README with verification rule DSL reference
- [ ] 8.2 Add examples for each new gate type in documentation
