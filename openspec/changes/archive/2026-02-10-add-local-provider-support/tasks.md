## 1. Local Provider Protocol and Registry
- [x] 1.1 Create `src/veridical/local/providers/` module with `__init__.py`
- [x] 1.2 Define `LocalProvider` Protocol class with methods: `build_command(task, error_context) -> str`, `default_mode() -> Literal["interactive", "subprocess"]`, `detect() -> bool`, and `name`/`description` properties
- [x] 1.3 Implement `LocalProviderRegistry` with `register()`, `resolve()`, `available()`, and `detect_available()` methods
- [x] 1.4 Add unit tests for `LocalProviderRegistry` (register, resolve, detect)

## 2. Claude Code Provider
- [x] 2.1 Implement `ClaudeCodeProvider` in `src/veridical/local/providers/claude_code.py`
- [x] 2.2 Support subprocess mode: `claude --print --output-format text -p "{task}"` with `--append-system-prompt` for error context
- [x] 2.3 Support interactive mode: bare `claude` command with env var error delivery
- [x] 2.4 Implement `detect()` via `shutil.which("claude")`
- [x] 2.5 Add unit tests for `ClaudeCodeProvider` (command construction, detection, error delivery)

## 3. Gemini CLI Provider
- [x] 3.1 Implement `GeminiCliProvider` in `src/veridical/local/providers/gemini_cli.py`
- [x] 3.2 Support subprocess mode: `gemini -p "{task_with_error_context}"` with error context appended to prompt
- [x] 3.3 Support interactive mode: bare `gemini` command with env var error delivery
- [x] 3.4 Implement `detect()` via `shutil.which("gemini")`
- [x] 3.5 Add unit tests for `GeminiCliProvider` (command construction, detection, error delivery)

## 4. Provider-Aware LocalRunner
- [x] 4.1 Extend `LocalRunner` to accept an optional `LocalProvider` parameter
- [x] 4.2 When a provider is set, delegate command construction to `provider.build_command()` on each iteration
- [x] 4.3 Preserve backward compatibility: no provider = existing `worker_command` + env var behavior
- [x] 4.4 Add unit tests for `LocalRunner` with and without provider

## 5. Configuration
- [x] 5.1 Add `provider: str | None` field to `LocalConfig` in `config/schema.py` (default: `None`)
- [x] 5.2 Add validation: if `provider` is set, resolve it from `LocalProviderRegistry` at config load time
- [x] 5.3 Update `.veridical.yaml.template` with `local.provider` examples for `claude-code` and `gemini-cli`

## 6. CLI Integration
- [x] 6.1 Add `--provider` / `-p` option to `veri local` command
- [x] 6.2 Add `--list-providers` flag that displays available providers with detection status and exits
- [x] 6.3 Implement auto-detection: when no provider/worker specified, detect available providers and auto-select or prompt
- [x] 6.4 Wire provider resolution into `run_local_supervisor()` — resolve provider, pass to `LocalRunner`

## 7. LocalSupervisor Integration
- [x] 7.1 Update `LocalSupervisor` to pass provider to `LocalRunner` when available
- [x] 7.2 Use provider's `default_mode()` when mode is not explicitly configured

## 8. Testing
- [x] 8.1 Add integration test: `veri local --provider claude-code --dry-run` resolves provider correctly
- [x] 8.2 Add integration test: `veri local --list-providers` outputs expected table
- [x] 8.3 Add integration test: auto-detection selects correct provider when one is on PATH

## 9. Documentation
- [x] 9.1 Update README with local provider section and usage examples
- [x] 9.2 Update `.veridical.yaml.template` with provider configuration examples
