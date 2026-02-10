## Context
Veridical's local loop mode (`veri local`) works with any shell command via `--worker` or `local.worker_command`. However, each AI coding tool has its own CLI flags, error delivery mechanisms, and interaction patterns. Users must manually figure out the right incantation for each tool. With Jules working end-to-end and the Worker abstraction layer in place, we can now offer named provider presets that encapsulate tool-specific knowledge while keeping the door open for deeper integrations.

## Goals / Non-Goals
- **Goals**:
  - Provide zero-config presets for Claude Code and Gemini CLI
  - Introduce a `LocalProvider` abstraction that encapsulates command construction, error delivery, and mode selection
  - Support auto-detection of available providers (check PATH)
  - Design the provider interface so it can evolve into a full `Worker` protocol implementation later
  - Keep backward compatibility — `--worker` and `local.worker_command` continue to work
- **Non-Goals**:
  - Building full Worker protocol implementations for Claude Code or Gemini CLI (future work)
  - Supporting Claude Code's SDK/API directly (future work)
  - Supporting Gemini's API directly (future work)
  - Managing provider-specific authentication (users handle their own auth)

## Decisions

### 1. LocalProvider Protocol
- **Decision**: Define a `LocalProvider` protocol with methods: `build_command(task, error_context) -> str`, `error_delivery_strategy() -> ErrorDeliveryStrategy`, `default_mode() -> Literal["interactive", "subprocess"]`, and `detect() -> bool` (checks if the tool is available on PATH).
- **Why**: This is a thin layer on top of `LocalRunner` that knows how to construct the right command for each tool. It's simpler than a full Worker implementation but captures the essential per-tool knowledge.
- **Alternatives considered**: (a) Just document the commands in README — rejected because it's error-prone and doesn't enable auto-detection. (b) Jump straight to full Worker implementations — rejected as premature; the local loop's simplicity (run command → verify → loop) doesn't need the dispatch/poll/sync lifecycle for tools that edit files in-place.

### 2. Error Delivery Strategies
- **Decision**: Support three error delivery strategies: `env_var` (current default), `prompt_append` (append error context to the task prompt passed as CLI argument), and `file` (write error context to a temp file, pass path via env var).
- **Why**: Different tools consume error feedback differently:
  - **Claude Code**: Supports `--append-system-prompt` for injecting context, and can read env vars. Best approach: pass error context via `--append-system-prompt` flag in subprocess mode, or env var in interactive mode.
  - **Gemini CLI**: Supports prompt text as a positional argument. Best approach: append error context to the prompt text.
  - **Generic**: Env var (existing behavior) works for custom scripts.

### 3. Provider Registry (not WorkerRegistry)
- **Decision**: Create a separate `LocalProviderRegistry` in `src/veridical/local/providers/` rather than reusing `WorkerRegistry`. Register providers at import time.
- **Why**: Local providers are a different abstraction than Workers. A provider produces a configured command for `LocalRunner`; a Worker implements the full dispatch/poll/sync lifecycle. Keeping them separate avoids confusion and allows providers to graduate to Workers independently.

### 4. CLI Integration
- **Decision**: Add `--provider` / `-p` option to `veri local`. When set, it overrides `--worker` and `local.worker_command`. Add `veri local --list-providers` to show available providers with detection status.
- **Why**: Named providers are the primary UX improvement. Auto-detection lets `veri local` suggest or auto-select a provider when neither `--provider` nor `--worker` is specified.

### 5. Provider-Specific Details

#### Claude Code (`claude-code`)
- **Command (subprocess)**: `claude --print --output-format text -p "{task_with_context}"`
- **Command (interactive)**: `claude` (user interacts directly)
- **Error delivery**: `--append-system-prompt "Previous verification failed: {error_context}"` in subprocess mode; `VERIDICAL_ERROR_CONTEXT` env var in interactive mode
- **Detection**: `which claude` succeeds
- **Default mode**: `subprocess`

#### Gemini CLI (`gemini-cli`)
- **Command (subprocess)**: `gemini -p "{task_with_context}"`
- **Command (interactive)**: `gemini` (user interacts directly)
- **Error delivery**: Error context appended to prompt text in subprocess mode; `VERIDICAL_ERROR_CONTEXT` env var in interactive mode
- **Detection**: `which gemini` succeeds
- **Default mode**: `subprocess`

### 6. Future Path to Full Worker Implementations
- The `LocalProvider` interface is designed so that a provider can optionally implement the full `Worker` protocol. When it does, `LocalSupervisor` can delegate to it directly instead of going through `LocalRunner`. This is a future enhancement — for now, all providers produce shell commands consumed by `LocalRunner`.

## Risks / Trade-offs
- **Risk**: CLI flags for Claude Code or Gemini CLI may change across versions → Mitigation: version-pin the known flags in provider presets; log warnings if the tool version is unrecognized.
- **Risk**: Auto-detection may find the wrong binary (e.g., a different `claude` on PATH) → Mitigation: detection also runs `claude --version` and checks for expected output patterns.
- **Trade-off**: Presets are less flexible than full Worker implementations → Acceptable for now; the architecture supports graduation to full Workers without breaking changes.

## Open Questions
- Should `veri local --provider claude-code` automatically switch to interactive mode if it detects a TTY, or always default to subprocess?
- Should providers support a `--model` flag override (e.g., `veri local --provider claude-code --model sonnet`)?
