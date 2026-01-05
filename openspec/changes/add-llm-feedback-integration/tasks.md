## 1. Configuration
- [ ] 1.1 Add `feedback_mode: Literal["heuristic", "rlm", "auto"]` to VerifierConfig
- [ ] 1.2 Add `rlm_threshold: int = 1000` for line count trigger
- [ ] 1.3 Document configuration options in schema docstrings

## 2. Feedback Generator Updates
- [ ] 2.1 Accept optional `LocalLLMClient` in `FeedbackGenerator.__init__()`
- [ ] 2.2 Implement `_summarize_with_llm()` async method
- [ ] 2.3 Implement `_chunk_and_summarize()` for recursive summarization
- [ ] 2.4 Add mode selection logic in `generate_feedback()`

## 3. LLM Prompting
- [ ] 3.1 Create system prompt for error extraction
- [ ] 3.2 Design prompt template for chunk summarization
- [ ] 3.3 Implement structured output parsing for file:line:message format
- [ ] 3.4 Add fallback to heuristic mode on LLM failure

## 4. Integration
- [ ] 4.1 Initialize LLM client in Verifier when config is present
- [ ] 4.2 Pass client to FeedbackGenerator
- [ ] 4.3 Add proper async lifecycle management (open/close)

## 5. Testing
- [ ] 5.1 Add unit tests with mocked LLM responses
- [ ] 5.2 Add integration test with actual local LLM (marked as slow)
- [ ] 5.3 Add test for graceful fallback on LLM timeout
- [ ] 5.4 Add test for recursive summarization of large logs
