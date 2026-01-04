# Change: Implement RLM-based Local Log Analysis

## Why
Current verification feedback relies on simple keyword-based truncation (`compress_log_output`). As highlighted in paper 2512.24601v1 ("Recursive Language Models"), heuristic filtering fails significantly on information-dense or large contexts (like 1000+ line stack traces or complex integration test failures). This leads to poor feedback for the remote agent, causing stuck loops. By applying RLM principles—specifically offloading context analysis to a local model—we can generate precise, reasoning-based failure summaries.

## What Changes
- Add optional integration with local OpenAI-compatible LLM endpoints (e.g., Ollama, vLLM).
- Enhance `Verifier` to support an `rlm-analyze` mode for feedback generation.
- Implement a recursive summarization strategy for logs exceeding the token window.
- **BREAKING**: None (this is an additive optional feature).

## Impact
- **specs/verifier**: New requirement for LLM-based feedback generation.
- **specs/config**: New configuration for local LLM endpoint.
- **code/verifier**: New `LogAnalyzer` class implementing the RLM strategy.
