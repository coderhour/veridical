## 1. Configuration
- [ ] 1.1 Add `parallel: bool = False` field to `QualityGate` schema
- [ ] 1.2 Add `parallel_timeout: int = 600` field to `VerifierConfig` schema
- [ ] 1.3 Update default configuration templates with parallel examples

## 2. Implementation
- [ ] 2.1 Create `_group_gates()` method to batch parallel vs sequential gates
- [ ] 2.2 Implement `_run_parallel_batch()` using `asyncio.gather()`
- [ ] 2.3 Update `run_all()` to process batches appropriately
- [ ] 2.4 Handle fail-fast: cancel remaining parallel gates if required gate fails

## 3. Testing
- [ ] 3.1 Add unit tests for gate grouping logic
- [ ] 3.2 Add unit tests for parallel execution with mocked gates
- [ ] 3.3 Add integration test verifying actual parallel speedup
- [ ] 3.4 Add test for fail-fast cancellation behavior

## 4. Documentation
- [ ] 4.1 Update README with parallel gate configuration examples
- [ ] 4.2 Update `.veridical.yaml.template` with parallel gate comments
