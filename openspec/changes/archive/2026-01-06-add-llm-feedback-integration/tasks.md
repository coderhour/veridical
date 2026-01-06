## 1. Configuration
- [x] 1.1 Add `feedback_mode: Literal["heuristic", "rlm", "auto"]` to VerifierConfig
- [x] 1.2 Add `rlm_threshold: int = 1000` for line count trigger
- [x] 1.3 Document configuration options in schema docstrings

## 2. Feedback Generator Updates
- [x] 2.1 Accept optional `LocalLLMClient` in `FeedbackGenerator.__init__()`
- [x] 2.2 Implement `_summarize_with_llm()` async method
- [x] 2.3 Implement `_chunk_and_summarize()` for recursive summarization
- [x] 2.4 Add mode selection logic in `generate_feedback()`

## 3. LLM Prompting
- [x] 3.1 Create system prompt for error extraction
- [x] 3.2 Design prompt template for chunk summarization
- [x] 3.3 Implement structured output parsing for file:line:message format
- [x] 3.4 Add fallback to heuristic mode on LLM failure

## 4. Integration
- [x] 4.1 Initialize LLM client in Verifier when config is present
- [x] 4.2 Pass client to FeedbackGenerator
- [x] 4.3 Add proper async lifecycle management (open/close)

## 5. Testing
- [x] 5.1 Add unit tests with mocked LLM responses
- [x] 5.2 Add integration test with actual local LLM (marked as slow)
- [x] 5.3 Add test for graceful fallback on LLM timeout
- [x] 5.4 Add test for recursive summarization of large logs
