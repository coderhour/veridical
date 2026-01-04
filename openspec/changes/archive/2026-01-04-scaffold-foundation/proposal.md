# Proposal: Scaffold Foundation for Project Veridical

## 1. Context & Problem Statement

Project Veridical aims to be a **Local Supervisory Control System** for Google Jules, implementing autonomous quality assurance loops that enforce high code quality through iterative testing, linting, and spec-driven development. Currently, no implementation exists—only architectural documentation describing the intended system.

The core challenge is that Google Jules operates asynchronously in cloud VMs, introducing significant latency (5-10 minutes per iteration) and state isolation. Unlike local agents (e.g., Claude Code with Ralph), the feedback loop is disconnected from the developer's environment. Without a robust supervisory layer, Jules may:
- Produce code that passes remote tests but fails local quality gates
- Drift from original intent due to context decay
- Consume costly VM resources in stuck loops
- Modify files outside the declared scope (security risk)

## 2. Proposed Solution

Scaffold the foundational Python package structure and core component interfaces for Project Veridical. This foundation establishes:

1. **Package Structure**: `src/veridical/` with modular components
2. **Five Core Components**: Supervisor, Dispatcher, Poller, Synchronizer, Verifier
3. **CLI Interface**: `veridical` command with subcommands (fix, verify, status, config)
4. **Configuration System**: YAML-based config with environment variable overrides
5. **Jules API Client**: Async HTTP client for `jules.googleapis.com/v1alpha`
6. **Type System**: Strict typing with dataclasses/Pydantic models
7. **Testing Infrastructure**: pytest setup with fixtures and mocks

This proposal focuses on **interfaces and scaffolding only**—business logic implementation will follow in subsequent proposals.

## 3. Scope Definition

| In Scope | Out of Scope |
| :--- | :--- |
| Package structure (`src/veridical/`) | Full business logic implementation |
| Component interfaces (abstract base classes) | Jules API authentication flows |
| CLI skeleton with argument parsing | Ralph/Claude Code integration |
| Configuration loading from YAML | GitHub Actions CI/CD pipeline |
| Jules API client with typed models | Web dashboard / monitoring UI |
| pytest infrastructure and fixtures | Production deployment scripts |
| pyproject.toml with dependencies | OpenSpec CLI integration hooks |
| Type definitions and data models | Parallel consensus ("Duel Mode") |

## 4. Risk Analysis

### Technical Risks
- **Jules API Stability**: The API is `v1alpha` and may change. Mitigation: Abstract the client behind an interface to allow easy updates.
- **Async Complexity**: Managing polling loops and timeouts is error-prone. Mitigation: Use `asyncio` with well-tested patterns and comprehensive timeout handling.
- **Git Operations**: Patch application can fail in complex merge scenarios. Mitigation: Create isolation branches and validate patches before applying.

### Security Risks
- **API Key Exposure**: Jules API keys must be protected. Mitigation: Load from environment variables only, never from config files.
- **Scope Violations**: Agents may modify unauthorized files. Mitigation: Implement diff inspection in Synchronizer (deferred to implementation phase).

### Project Risks
- **Scope Creep**: Foundation work could expand into implementation. Mitigation: Strict adherence to "interfaces only" in this proposal; implementation in follow-up proposals.

## 5. Success Criteria

- [ ] `uv sync` installs all dependencies without errors
- [ ] `veridical --help` displays CLI usage information
- [ ] `veridical --version` displays version number
- [ ] `pytest` discovers and runs placeholder tests (may be skipped)
- [ ] `ruff check src/` passes with zero errors
- [ ] `mypy src/` passes with zero type errors
- [ ] All five component modules import without errors
- [ ] Jules API client models validate sample JSON payloads
