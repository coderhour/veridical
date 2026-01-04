## 1. Configuration
- [ ] 1.1 Update `VeridicalConfig` to include optional `local_llm` section (base_url, model, timeout).
- [ ] 1.2 Update `config.init` template to include commented-out local LLM example.

## 2. Core Implementation
- [ ] 2.1 Create `src/veridical/lld/` (Local LLM Dispatcher) module for generic OpenAI-compatible client.
- [ ] 2.2 Implement `LogAnalyzer` in `src/veridical/verifier/analysis.py` using RLM strategy (chunking + recursive summary).
- [ ] 2.3 Integrate `LogAnalyzer` into `FeedbackGenerator` as a fallback/alternative to `compress_log_output`.

## 3. Integration & Testing
- [ ] 3.1 specific unit tests for `LogAnalyzer` mocking the LLM response.
- [ ] 3.2 Integration test with a mocked local server endpoint.
- [ ] 3.3 Verify RLM behavior on a large sample log file (>10k lines).
