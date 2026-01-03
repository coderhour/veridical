# Design: Project Veridical Foundation Architecture

## 1. Architectural Overview

Project Veridical implements a **Control Loop Architecture** inspired by feedback control systems. The system manages probabilistic LLM agents (Google Jules) by imposing deterministic constraints through iterative verification.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DEVELOPER MACHINE                          │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │     CLI      │───▶│  Supervisor  │───▶│    Configuration     │  │
│  │   veridical  │    │   (Kernel)   │    │  .veridical.yaml     │  │
│  └──────────────┘    └──────┬───────┘    └──────────────────────┘  │
│                             │                                       │
│         ┌───────────────────┼───────────────────┐                  │
│         │                   │                   │                  │
│         ▼                   ▼                   ▼                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│  │  Dispatcher  │    │    Poller    │    │ Synchronizer │         │
│  │              │    │              │    │              │         │
│  │ - Prompts    │    │ - Status     │    │ - Git ops    │         │
│  │ - Sessions   │    │ - Backoff    │    │ - Patches    │         │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘         │
│         │                   │                   │                  │
│         └───────────────────┼───────────────────┘                  │
│                             │                                       │
│                             ▼                                       │
│                      ┌──────────────┐                              │
│                      │   Verifier   │                              │
│                      │              │                              │
│                      │ - Tests      │                              │
│                      │ - Linters    │                              │
│                      └──────────────┘                              │
│                                                                     │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS (jules.googleapis.com)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         GOOGLE CLOUD                                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                     Jules VM (Ephemeral)                      │  │
│  │                                                                │  │
│  │  - Clones repository                                           │  │
│  │  - Reads AGENTS.md                                             │  │
│  │  - Executes tasks                                              │  │
│  │  - Generates patches/PRs                                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. Package Structure

```
src/veridical/
├── __init__.py              # Package version, public API exports
├── __main__.py              # Entry point for `python -m veridical`
├── cli/
│   ├── __init__.py
│   ├── main.py              # CLI argument parsing (click/typer)
│   ├── fix.py               # `veridical fix` command
│   ├── verify.py            # `veridical verify` command
│   ├── status.py            # `veridical status` command
│   └── config.py            # `veridical config` command
├── supervisor/
│   ├── __init__.py
│   ├── loop.py              # Main control loop logic
│   ├── state.py             # State machine and transitions
│   └── circuit_breaker.py   # Circuit breaker patterns
├── dispatcher/
│   ├── __init__.py
│   ├── prompt.py            # Sandwich prompt construction
│   ├── session.py           # Session creation and management
│   └── agents_md.py         # Dynamic AGENTS.md injection
├── poller/
│   ├── __init__.py
│   ├── monitor.py           # Status polling logic
│   └── backoff.py           # Intelligent backoff strategies
├── synchronizer/
│   ├── __init__.py
│   ├── git.py               # Git operations wrapper
│   ├── branch.py            # Branch management
│   └── patch.py             # Patch application
├── verifier/
│   ├── __init__.py
│   ├── runner.py            # Test/lint execution
│   ├── feedback.py          # Error summarization
│   └── quality_gate.py      # Pass/fail determination
├── api/
│   ├── __init__.py
│   ├── client.py            # Async HTTP client for Jules API
│   ├── models.py            # Pydantic models for API payloads
│   └── exceptions.py        # Custom API exceptions
├── config/
│   ├── __init__.py
│   ├── loader.py            # YAML config loading
│   ├── schema.py            # Config validation schema
│   └── defaults.py          # Default configuration values
└── models/
    ├── __init__.py
    ├── session.py           # Session state models
    ├── iteration.py         # Iteration tracking models
    └── result.py            # Verification result models
```

## 3. Component Design Decisions

### 3.1 Supervisor (Kernel)

**Decision**: Implement as a finite state machine with explicit state transitions.

**Rationale**: The supervisor loop has discrete states (IDLE, DISPATCHING, POLLING, SYNCING, VERIFYING, SUCCESS, FAILED). A state machine provides:
- Clear documentation of valid transitions
- Easy debugging and logging
- Prevention of invalid state combinations

**States**:
```
IDLE ─────▶ DISPATCHING ─────▶ POLLING ─────▶ SYNCING ─────▶ VERIFYING
  ▲              │                 │              │              │
  │              │                 │              │              │
  │              ▼                 ▼              ▼              ▼
  └────────── FAILED ◀────────────┴──────────────┴──────────────┘
                                                                 │
                                                                 ▼
                                                             SUCCESS
```

### 3.2 Dispatcher

**Decision**: Use a "Sandwich Prompt" template system with Jinja2.

**Rationale**: Prompts need three layers:
1. **Role Layer**: Static persona definition ("You are a Senior Principal Engineer...")
2. **Intent Layer**: User's task description (dynamic)
3. **Constraint Layer**: Quality rules and current error context (dynamic)

Jinja2 templates allow non-developers to customize prompts without code changes.

### 3.3 Poller

**Decision**: Implement exponential backoff with jitter.

**Rationale**: Jules VMs take 5-10 minutes. Polling every second wastes resources; polling every 5 minutes loses responsiveness. Exponential backoff (30s → 60s → 120s, max 300s) with random jitter prevents thundering herd if multiple sessions run.

### 3.4 Synchronizer

**Decision**: Use isolation branches, never modify main directly.

**Rationale**: If a patch fails verification, we need to cleanly discard it. Git branches provide atomic isolation. Pattern:
1. Create `veridical/iter-{n}` branch from main
2. Apply patch to branch
3. Run verification
4. If pass: merge to main; If fail: delete branch

### 3.5 Verifier

**Decision**: Execute commands from `.veridical.yaml`, capture structured output.

**Rationale**: Projects have different test runners (pytest, jest, make test). The verifier should be agnostic—it runs configured commands and parses exit codes. Structured output (JSON test results) enables better feedback generation.

## 4. Technology Choices

### 4.1 CLI Framework: Typer

**Choice**: [Typer](https://typer.tiangolo.com/) over Click or argparse.

**Rationale**:
- Type hints generate CLI arguments automatically
- Built-in `--help` generation
- Rich integration for colored output
- Async command support

### 4.2 HTTP Client: HTTPX

**Choice**: [HTTPX](https://www.python-httpx.org/) over requests or aiohttp.

**Rationale**:
- Native async/await support
- HTTP/2 support (future-proofing)
- Compatible with `requests` API (familiar)
- Excellent timeout and retry handling

### 4.3 Configuration: Pydantic Settings

**Choice**: [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) for configuration.

**Rationale**:
- YAML/JSON/TOML loading built-in
- Environment variable override support
- Type validation at load time
- Excellent IDE support

### 4.4 Data Models: Pydantic v2

**Choice**: Pydantic v2 for all data models.

**Rationale**:
- Rust-based core (performance)
- JSON Schema generation for API validation
- Seamless serialization/deserialization
- Discriminated unions for state machines

## 5. Dependency Strategy

### Production Dependencies
```toml
[project.dependencies]
typer = ">=0.12.0"
httpx = ">=0.27.0"
pydantic = ">=2.5.0"
pydantic-settings = ">=2.1.0"
pyyaml = ">=6.0"
rich = ">=13.0.0"
jinja2 = ">=3.1.0"
gitpython = ">=3.1.0"
```

### Development Dependencies
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.4.0",
    "mypy>=1.8.0",
    "respx>=0.21.0",  # HTTPX mocking
]
```

## 6. Error Handling Strategy

All components use a consistent exception hierarchy:

```python
class VeridicalError(Exception):
    """Base exception for all Veridical errors."""

class ConfigurationError(VeridicalError):
    """Invalid configuration."""

class APIError(VeridicalError):
    """Jules API communication error."""

class SynchronizationError(VeridicalError):
    """Git/patch operation failed."""

class VerificationError(VeridicalError):
    """Quality gate failed (not a system error)."""

class CircuitOpenError(VeridicalError):
    """Circuit breaker tripped, aborting loop."""
```

## 7. Logging Strategy

Use `structlog` for structured JSON logging:
- **DEBUG**: Detailed component operations
- **INFO**: Loop iterations, state transitions
- **WARNING**: Recoverable issues, retries
- **ERROR**: Failures requiring attention

Log format includes: `timestamp`, `level`, `component`, `iteration`, `session_id`, `message`.

## 8. Future Considerations

### Not in This Proposal (Deferred)
- **Authentication**: OAuth/service account flows for Jules API
- **Parallel Consensus**: "Duel Mode" spawning multiple sessions
- **Ralph Integration**: Claude Code autonomous loops
- **Telemetry**: Usage metrics and cost tracking
- **Plugins**: Extensible verifier commands

These are documented here to ensure the foundation accommodates them without requiring refactoring.
