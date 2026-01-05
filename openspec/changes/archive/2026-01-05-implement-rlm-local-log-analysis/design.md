## Context
The verification process often generates massive log files (stdout/stderr) that exceed the context window of the remote agent (Jules). Simple truncation logic (`head` + `tail` + `grep error`) often misses the root cause, especially if the error is a logic failure printed without "error" keywords. Paper 2512.24601v1 suggests that Recursive Language Models (RLMs) can effectively manage huge contexts by recursively processing and summarizing information.

## Decisions
- **Decision**: Use a **Simplified Sequential RLM Pattern**.
  - Instead of a full REPL agent, we will implement a chunk-based recursive summarizer: `Summary(Chunk_N) = LLM(Chunk_N + Summary(Chunk_N-1))`.
  - This avoids need for complex tool-use support in the local model, enabling support for smaller/dumber local models (e.g. Qwen-7B, Llama-3-8B).
- **Decision**: Use `openai` python package (or raw `httpx`) compatible with Local Inference Servers (Ollama/vLLM).
  - Keeps dependency footprint low (standard protocol).
- **Decision**: Make it strictly optional.
  - Users without a GPU/Local LLM can continue using the regex heuristic.

## Risks / Trade-offs
- **Latency**: Local inference can be slow. We will set a strict timeout (e.g. 30s per chunk) and fallback to heuristic if it times out.
- **Accuracy**: Small local models might hallucinate. We prompt the model to quote specific lines from the log.

## Open Questions
- Should we support remote LLMs (e.g. OpenAI API) for this too?
  - Yes, the configuration will just take a generic `base_url` and `api_key`, so it works for both.
