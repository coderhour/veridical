## 1. Configuration
- [x] 1.1 Add `parallel: bool = False` field to `QualityGate` schema
- [x] 1.2 Add `parallel_timeout: int = 600` field to `VerifierConfig` schema
- [x] 1.3 Update default configuration templates with parallel examples

## 2. Implementation
- [x] 2.1 Create `_group_gates()` method to batch parallel vs sequential gates
- [x] 2.2 Implement `_run_parallel_batch()` using `asyncio.gather()`
- [x] 2.3 Update `run_all()` to process batches appropriately
- [x] 2.4 Handle fail-fast: cancel remaining parallel gates if required gate fails

## 3. Testing
- [x] 3.1 Add unit tests for gate grouping logic
- [x] 3.2 Add unit tests for parallel execution with mocked gates
- [x] 3.3 Add integration test verifying actual parallel speedup
- [x] 3.4 Add test for fail-fast cancellation behavior

## 4. Documentation
- [x] 4.1 Update README with parallel gate configuration examples
- [x] 4.2 Update `.veridical.yaml.template` with parallel gate comments
