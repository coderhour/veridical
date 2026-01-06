# Change: Wire Local LLM into Feedback Generation

## Why
The `LocalLLMClient` exists but isn't wired into the main feedback loop. Error output is truncated at a fixed length, losing critical context. Using the LLM for recursive summarization would extract actionable errors and dramatically improve Jules' ability to fix issues on subsequent iterations.

## What Changes
- Wire `LocalLLMClient` into `FeedbackGenerator` when configured
- Implement recursive chunk summarization for large outputs
- Extract actionable error patterns (file:line:message)
- Add `feedback_mode` config option: "heuristic", "rlm", or "auto"

## Impact
- Affected specs: verifier
- Affected code: `src/veridical/verifier/feedback.py`, `src/veridical/lld/client.py`, `src/veridical/config/schema.py`
