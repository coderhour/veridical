# Change: Add Work Log Persistence

## Why
Users currently have no way to audit what happened during Veridical iterations after the fact. When debugging failures or reviewing agent decisions, there's no persistent record of the inputs (prompts, error context) and outputs (session results, verification results) for each iteration. A structured work log would enable post-hoc analysis and accountability.

## What Changes
- Add a new `worklog` capability for recording iteration history
- Create a `worklog/` directory in the project folder (alongside `.veridical.yaml`)
- Organize logs by date (`worklog/YYYY-MM-DD/`)
- Record each iteration as a structured entry with timestamp, inputs, and outputs
- Auto-create directory structure when logging

## Impact
- Affected specs: NEW `worklog` capability
- Affected code: `src/veridical/supervisor/loop.py` (emit log entries), `src/veridical/config/schema.py` (optional config)
