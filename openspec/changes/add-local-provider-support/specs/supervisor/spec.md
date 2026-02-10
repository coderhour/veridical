## ADDED Requirements

### Requirement: Local Provider Protocol
The system SHALL define a `LocalProvider` protocol that encapsulates tool-specific configuration for local AI coding agents.

#### Scenario: LocalProvider Protocol Methods
- **WHEN** implementing the `LocalProvider` protocol
- **THEN** the implementation SHALL provide `build_command(task: str, error_context: str | None) -> str` to construct the shell command
- **AND** it SHALL provide `default_mode() -> Literal["interactive", "subprocess"]` to indicate the preferred execution mode
- **AND** it SHALL provide `detect() -> bool` to check if the tool is available on PATH
- **AND** it SHALL provide `name` and `description` string properties

#### Scenario: LocalProvider Structural Typing
- **WHEN** a class implements `build_command`, `default_mode`, `detect`, `name`, and `description` with correct signatures
- **THEN** it SHALL satisfy the `LocalProvider` protocol without explicit inheritance

### Requirement: Claude Code Provider
The system SHALL provide a `ClaudeCodeProvider` that configures the local runner for Anthropic's Claude Code CLI.

#### Scenario: Claude Code Subprocess Command
- **WHEN** `ClaudeCodeProvider.build_command(task, error_context)` is called
- **AND** the mode is `subprocess`
- **THEN** it SHALL return a command using `claude --print --output-format text -p "{task}"`
- **AND** if `error_context` is provided, it SHALL append `--append-system-prompt` with the verification feedback

#### Scenario: Claude Code Interactive Command
- **WHEN** `ClaudeCodeProvider.build_command(task, error_context)` is called
- **AND** the mode is `interactive`
- **THEN** it SHALL return `claude` for interactive TTY usage
- **AND** error context SHALL be delivered via the `VERIDICAL_ERROR_CONTEXT` environment variable

#### Scenario: Claude Code Detection
- **WHEN** `ClaudeCodeProvider.detect()` is called
- **THEN** it SHALL return `True` if `claude` is found on PATH
- **AND** it SHALL return `False` otherwise

### Requirement: Gemini CLI Provider
The system SHALL provide a `GeminiCliProvider` that configures the local runner for Google's Gemini CLI.

#### Scenario: Gemini CLI Subprocess Command
- **WHEN** `GeminiCliProvider.build_command(task, error_context)` is called
- **AND** the mode is `subprocess`
- **THEN** it SHALL return a command using `gemini -p "{task_with_error_context}"`
- **AND** if `error_context` is provided, it SHALL append the verification feedback to the prompt text

#### Scenario: Gemini CLI Interactive Command
- **WHEN** `GeminiCliProvider.build_command(task, error_context)` is called
- **AND** the mode is `interactive`
- **THEN** it SHALL return `gemini` for interactive TTY usage
- **AND** error context SHALL be delivered via the `VERIDICAL_ERROR_CONTEXT` environment variable

#### Scenario: Gemini CLI Detection
- **WHEN** `GeminiCliProvider.detect()` is called
- **THEN** it SHALL return `True` if `gemini` is found on PATH
- **AND** it SHALL return `False` otherwise

### Requirement: Provider-Aware Local Runner
The `LocalRunner` SHALL support receiving a `LocalProvider` to delegate command construction and error delivery.

#### Scenario: Runner with Provider
- **WHEN** `LocalRunner` is initialized with a `LocalProvider`
- **THEN** it SHALL use `provider.build_command()` to construct the command on each iteration
- **AND** it SHALL use the provider's error delivery strategy instead of the default env var approach

#### Scenario: Runner without Provider (Backward Compatibility)
- **WHEN** `LocalRunner` is initialized without a `LocalProvider`
- **THEN** it SHALL use `config.local.worker_command` as before
- **AND** it SHALL deliver error context via the `config.local.error_env_var` environment variable
- **AND** existing behavior SHALL be fully preserved
