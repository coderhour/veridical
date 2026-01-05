## 1. Configuration
- [x] 1.1 Add `ScopeValidationConfig` model with allowlist/denylist fields
- [x] 1.2 Add default denylist: `.github/`, `.gitlab-ci.yml`, `AGENTS.md`, `*.env`
- [x] 1.3 Add `scope_validation` section to GitConfig schema
- [x] 1.4 Add `strict_mode: bool` flag for blocking vs warning

## 2. Validator Implementation
- [x] 2.1 Create `ScopeValidator` class in `synchronizer/validator.py`
- [x] 2.2 Implement `validate_patch()` method that parses diff for file paths
- [x] 2.3 Implement pattern matching against allowlist/denylist
- [x] 2.4 Return `ValidationResult` with violations list

## 3. Integration
- [x] 3.1 Add validation step before `git apply` in `PatchApplier`
- [x] 3.2 Reject patch if strict_mode and violations found
- [x] 3.3 Log warnings if not strict_mode but violations found
- [x] 3.4 Include violation details in error feedback to Jules

## 4. Audit Logging
- [x] 4.1 Log all files modified by each patch
- [x] 4.2 Log rejected patches with violation reasons
- [x] 4.3 Add structured logging format for security events

## 5. Testing
- [x] 5.1 Add unit tests for pattern matching logic
- [x] 5.2 Add unit tests for diff parsing
- [x] 5.3 Add integration test with blocked patch
- [x] 5.4 Add test for warning mode (non-strict)
