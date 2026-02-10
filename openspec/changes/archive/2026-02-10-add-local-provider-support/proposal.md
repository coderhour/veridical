# Change: Add Local Provider Support for Claude Code and Gemini CLI

## Why
Veridical's local loop mode (`veri local`) currently requires users to manually configure shell commands for each AI coding tool. With Jules now working end-to-end and the Worker abstraction in place, we have the foundation to offer first-class support for popular local AI coding agents. Claude Code and Gemini CLI are the two most prominent local tools — providing named provider presets eliminates configuration friction and enables provider-specific optimizations (error delivery, prompt formatting, mode selection). The architecture should also make it trivial to add more providers in the future.

## What Changes
- Introduce a **local provider registry** that maps provider names (e.g., `claude-code`, `gemini-cli`) to preset configurations and optional provider-specific logic
- Add `ClaudeCodeProvider` preset: auto-configures the `claude` CLI command with appropriate flags (`--print` for subprocess mode, interactive for TTY), error delivery via `CLAUDE_CODE_ERROR_CONTEXT` env var and `--append-system-prompt` flag
- Add `GeminiCliProvider` preset: auto-configures the `gemini` CLI command with appropriate flags, error delivery via prompt injection
- Add `--provider` / `-p` option to `veri local` CLI that selects a named provider instead of requiring `--worker` command
- Add `local.provider` config field as an alternative to `local.worker_command` — when set, the provider preset auto-fills command, mode, and error delivery
- Design the provider interface to support future deeper `Worker` protocol implementations (e.g., using Claude Code's SDK or Gemini's API directly)
- Add provider detection: `veri local` can auto-detect available providers by checking if `claude` or `gemini` are on PATH

## Impact
- Affected specs: `config`, `cli`, `supervisor`
- Affected code: `src/veridical/local/`, `src/veridical/cli/local.py`, `src/veridical/config/schema.py`
- No breaking changes — existing `--worker` and `local.worker_command` continue to work unchanged
