# Design: Dynamic Spec Detection

## Architecture Overview

This feature adds a new `openspec` module to Veridical that enables dynamic detection and selection of OpenSpec changes during task execution.

```
src/veridical/
├── openspec/                 # NEW MODULE
│   ├── __init__.py
│   ├── scanner.py           # Scans for open specs
│   └── matcher.py           # Matches specs from task descriptions
├── cli/
│   ├── run.py               # MODIFIED - optional task, spec integration
│   └── spec_selector.py     # NEW - interactive selection UI
├── supervisor/
│   └── loop.py              # MODIFIED - pass spec context to verifier
└── verifier/
    └── quality_gate.py      # MODIFIED - handle path: auto
```

## Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLI: veri run                            │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  1. Scan for open specs via scanner.find_open_specs()           │
│     Returns: List[OpenSpecInfo]                                  │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  2. If task provided:                                            │
│     - Try matcher.match_spec_from_description(task, specs)       │
│     - If matched: use that spec                                  │
│     - If not matched but specs exist: show selector              │
│                                                                  │
│  3. If no task provided:                                        │
│     - Show spec_selector for interactive choice                 │
│     - Generate task: "Implement spec <name>"                    │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  4. Store selected spec in SpecContext                          │
│     - spec_name: str | None                                      │
│     - tasks_file: Path | None                                    │
│     - task_description: str                                      │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  5. Pass SpecContext to Supervisor.run()                        │
│     - Supervisor stores context for verifier access              │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  6. Verifier checks task_completion gate:                       │
│     - If path: auto → look up from SpecContext                   │
│     - If path: <explicit> → use explicit path                    │
│     - If no spec selected → skip task_completion gate            │
└──────────────────────────────────────────────────────────────────┘
```

## Key Data Structures

### OpenSpecInfo
```python
@dataclass
class OpenSpecInfo:
    """Information about an OpenSpec change with open tasks."""
    name: str                    # e.g., "add-configurable-backoff-strategy"
    path: Path                   # e.g., openspec/changes/add-configurable-backoff-strategy/
    tasks_file: Path             # e.g., openspec/changes/.../tasks.md
    incomplete_count: int        # Number of incomplete tasks
    total_count: int             # Total tasks in file
```

### SpecContext
```python
@dataclass
class SpecContext:
    """Context for the currently selected spec."""
    spec: OpenSpecInfo | None    # Selected spec (None for bug fixes)
    task_description: str        # Final task description
    
    @property
    def tasks_file(self) -> Path | None:
        return self.spec.tasks_file if self.spec else None
```

## Matching Algorithm

The matcher uses a prioritized approach:

1. **Exact pattern match**: "Implement spec <name>" or "implement spec <name>"
2. **Partial pattern match**: "implement <name>" (without "spec")
3. **Fuzzy match**: Check if any spec name appears in the task description
4. **No match**: Return None, triggering interactive selection

```python
def match_spec_from_description(
    description: str, 
    specs: list[OpenSpecInfo]
) -> OpenSpecInfo | None:
    description_lower = description.lower()
    
    # Pattern 1: "implement spec <name>"
    if match := re.search(r"implement spec (\S+)", description_lower):
        spec_name = match.group(1)
        for spec in specs:
            if spec.name == spec_name:
                return spec
    
    # Pattern 2: Check if any spec name appears in description
    for spec in specs:
        if spec.name in description_lower:
            return spec
    
    return None
```

## Interactive Selection UI

```
╭──────────────────────────────────────────────────────────────╮
│                    Select OpenSpec Change                    │
├──────────────────────────────────────────────────────────────┤
│ Found 3 specs with incomplete tasks:                         │
│                                                              │
│   [1] add-configurable-backoff-strategy                      │
│       5 of 9 tasks incomplete                                │
│                                                              │
│   [2] add-extended-language-templates                        │
│       10 of 13 tasks incomplete                              │
│                                                              │
│   [3] implement-rlm-local-log-analysis                       │
│       8 of 8 tasks incomplete                                │
│                                                              │
│   [0] None - Skip task verification (bug fix / ad-hoc)       │
╰──────────────────────────────────────────────────────────────╯

Select spec [0-3]: 
```

## Config Changes

### Before
```yaml
verifier:
  quality_gates:
    - name: task_completion
      type: task_completion
      path: openspec/changes/add-task-completion-verifier/tasks.md  # Hardcoded!
```

### After (Option 1: Auto-detection)
```yaml
verifier:
  quality_gates:
    - name: task_completion
      type: task_completion
      path: auto  # Dynamic detection from CLI
```

### After (Option 2: Remove from config entirely)
The task_completion gate could be automatically injected when a spec is selected,
rather than being a user-configured quality gate. This is cleaner but less flexible.

**Recommendation**: Go with Option 1 for backward compatibility. Users can still
specify explicit paths if needed.

## CLI Interface Changes

### Current
```bash
veri run "Implement spec add-configurable-backoff-strategy"  # Required argument
```

### Proposed
```bash
# Zero-argument mode (interactive spec selection)
veri run

# Explicit task with auto-detection
veri run "Implement spec add-something"

# Skip task verification for bug fixes
veri run "Fix login bug" --no-spec
veri run "Fix login bug" --skip-tasks

# Resume session (unchanged)
veri run "Continue" --session-id abc123
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| No specs found, no task | Error: "No task provided and no open specs found. Provide a task description." |
| Spec matched but tasks.md missing | Warning, proceed without task verification |
| Interactive selection declined (Ctrl+C) | Exit with code 0, "Aborted" |
| `--no-spec` with task | Proceed without task verification, use provided task |

## Testing Strategy

1. **Unit Tests**: scanner, matcher, spec_selector modules
2. **Integration Tests**: Full flow with mocked prompt (monkeypatch typer.confirm)
3. **Manual Tests**: Interactive selection flow (documented in test plan)
