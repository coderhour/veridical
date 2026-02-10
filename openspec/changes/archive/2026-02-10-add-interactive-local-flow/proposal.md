# Change: Add interactive flow to `veri local`

## Why
Running `veri local` with no arguments currently falls back to a generic "Local autonomous task" placeholder. Users should get the same interactive experience as `veri run`: auto-detect a provider, present open specs for selection, and prompt for a task description if none is provided.

## What Changes
- When no task argument is given, show interactive spec selection (reusing `select_spec`) and prompt for task description
- Auto-select or prompt for provider when none specified (already implemented)
- If user selects "None" for spec or no specs exist, prompt for a free-text task description
- Add `--no-spec` / `--skip-tasks` flag to bypass spec selection (parity with `veri run`)

## Impact
- Affected specs: cli
- Affected code: `src/veridical/cli/local.py`, `src/veridical/cli/spec_selector.py` (reused)
