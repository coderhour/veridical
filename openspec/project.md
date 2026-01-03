# Project Context

## Purpose

**Project Veridical** is a Local Supervisory Control System for remote asynchronous coding agents, specifically designed to bridge the gap between Ralph's rigorous quality loops and Google Jules' scalable cloud architecture. The objective is to enforce high code quality through autonomous iterative testing, linter-guided refactoring, and strict adherence to OpenSpec contracts.

### Core Goals
- Implement a "Ralph-like" autonomous quality assurance loop for Google Jules
- Enforce rigorous code quality standards through local verification
- Bridge asynchronous cloud-based agents (Jules) with synchronous local validation
- Provide deterministic engineering outcomes from probabilistic LLM agents
- Establish spec-driven development workflows using OpenSpec protocol

## Tech Stack

### Core Technologies
- **Python 3.11+**: Primary implementation language
- **uv**: Modern Python package and dependency management
- **pyproject.toml**: Project configuration and metadata
- **pytest**: Testing framework with coverage reporting

### External Integrations
- **Google Jules API** (`jules.googleapis.com`): Remote asynchronous coding agent
- **Claude Code**: Local AI coding assistant (optional integration)
- **OpenSpec CLI** (`@fission-ai/openspec`): Spec-driven development framework
- **Git**: Version control and patch management

### Development Tools
- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checking

## Project Conventions

### Code Style
- Follow PEP 8 conventions with strict enforcement via `ruff`
- Use type hints for all function signatures and public APIs
- Maximum line length: 100 characters
- Use descriptive variable names; avoid single-letter variables except in comprehensions
- Docstrings required for all public modules, classes, and functions (Google style)
- No `# type: ignore` comments without justification in adjacent comment

### Architecture Patterns

Project Veridical follows a **Component-Based Control Loop Architecture** with five primary components:

#### 1. Supervisor (Kernel)
- Manages the main control loop, state machine, and decision logic
- Implements circuit breaker patterns to prevent runaway loops
- Tracks iteration counts and convergence metrics
- **Location**: `src/veridical/supervisor/`

#### 2. Dispatcher
- Formats prompts using the "Sandwich Strategy" (role + intent + constraints)
- Initiates remote Jules sessions via REST API
- Manages `requirePlanApproval=false` for autonomous operation
- Dynamically injects AGENTS.md constraints based on current error context
- **Location**: `src/veridical/dispatcher/`

#### 3. Poller
- Monitors asynchronous progress of remote Jules VMs
- Implements intelligent backoff polling (30s intervals)
- Detects state transitions: PENDING → RUNNING → COMPLETED/FAILED
- Auto-approves plans when stuck in WAITING_FOR_PLAN_APPROVAL
- **Location**: `src/veridical/poller/`

#### 4. Synchronizer
- Manages Git branches and applies remote patches locally
- Creates isolation branches (`veridical/iter-N`) for each iteration
- Handles patch application failures with context feedback
- Merges successful iterations to main branch
- **Location**: `src/veridical/synchronizer/`

#### 5. Verifier
- Runs local test suite, linters, and quality gates
- Does NOT trust remote VM self-reported success
- Captures and summarizes stderr/stdout for feedback
- Generates structured error context for next iteration
- **Location**: `src/veridical/verifier/`

### Design Principles
- **State Synchronization Pattern**: Local truth vs. remote clone divergence management
- **Asynchronous Loop Management**: Handle high-latency feedback cycles (5-10 min per iteration)
- **Prompt Precision over Brute Force**: Emphasize quality prompts due to iteration cost
- **Local Truth Verification**: Always verify remotely generated code locally
- **Spec-Driven Development**: All work must start with approved OpenSpec proposal

### Testing Strategy

#### Test Levels
1. **Unit Tests** (`tests/unit/`): Test individual component logic in isolation
   - Mock all external APIs (Jules, Git)
   - Test circuit breaker conditions, state transitions
   - Target: 90%+ coverage

2. **Integration Tests** (`tests/integration/`): Test component interactions
   - Use real Git operations on temporary repos
   - Mock only Jules API endpoints
   - Test patch application, branch management

3. **End-to-End Tests** (`tests/e2e/`): Full workflow validation
   - Requires Jules API access (run in CI with credentials)
   - Test complete loop: dispatch → poll → sync → verify → iterate
   - Uses test fixtures with known-good/known-bad code

#### Test Execution
```bash
# Run all tests with coverage
pytest --cov=src/veridical --cov-report=term-missing

# Run only fast tests (exclude e2e)
pytest -m "not e2e"

# Run with verbose output
pytest -v
```

#### Quality Gates
- All PRs must pass `pytest` with 0 failures
- Coverage must not decrease below current baseline
- `ruff check` must pass with 0 errors
- `mypy` must pass with 0 type errors

### Git Workflow

#### Branching Strategy
- **main**: Production-ready code, protected branch
- **veridical/iter-N**: Temporary branches created by Synchronizer for each Jules iteration
- **feature/SPEC-ID**: Human-driven feature branches following OpenSpec change IDs
- **fix/issue-NNN**: Hotfix branches for critical bugs

#### Commit Conventions
Follow Conventional Commits specification:
- `feat:` New feature implementation
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions or modifications
- `refactor:` Code refactoring without behavior change
- `chore:` Build, tooling, dependency updates

#### Commit Attribution
All agent-generated commits must include:
```
Co-Authored-By: Google Jules <noreply@google.com>
# or
Co-Authored-By: Claude Sonnet <noreply@anthropic.com>
```

## Domain Context

### Control Theory for Agentic Systems
Project Veridical applies **control theory** concepts to manage probabilistic LLM agents:

- **Feedback Loop**: Local verification provides error signals back to remote agent
- **Circuit Breaker**: Prevents infinite loops via stagnation detection
- **Convergence Detection**: Monitors task completion and code stability
- **State Synchronization**: Manages divergence between local and remote git states

### Key Terminology
- **Supervisor Loop**: The main while loop that iterates until quality gates pass or max iterations reached
- **Sandwich Prompt**: Three-layer prompt structure (role definition + user intent + constraint injection)
- **Spec Delta**: OpenSpec artifact describing ADDED/MODIFIED/REMOVED requirements
- **Zombie Agent**: Security vulnerability where prompt injection causes unauthorized actions
- **Stuck Loop**: Agent repeatedly attempts same failed fix without progress

### OpenSpec Integration
This project strictly follows the **OpenSpec protocol** for spec-driven development:

1. **No code without approved proposal**: All implementation must start with `openspec/changes/<id>/proposal.md`
2. **Task-driven execution**: Agents execute `tasks.md` sequentially, marking checkboxes as complete
3. **Spec deltas over direct edits**: Changes to specifications are written as deltas, merged via `openspec archive`
4. **Immutable source of truth**: `openspec/specs/` is read-only during development, updated only via archive process

Refer to `openspec/AGENTS.md` for detailed workflow instructions.

## Important Constraints

### API Rate Limits
- **Google Jules**: 60 tasks/day (Ultra tier), max 5 concurrent sessions
- **Claude Code**: ~100 calls/hour (varies by subscription)
- Veridical implements Token Bucket Semaphore pattern in `.veridical_state.json`

### Security Constraints
- **Scope Enforcement**: Agent must not modify files outside declared scope in proposal
- **Diff Inspection**: All patches inspected before application; circuit trips on suspicious changes
- **No Secrets**: Never commit `.env`, `credentials.json`, or API keys
- **Zombie Defense**: Reject patches that modify CI/CD or auth infrastructure unless explicitly scoped

### Cost Management
- Each Jules iteration costs VM time (~5-10 minutes)
- Maximum iteration limit: 10 per task (configurable via `--max-iterations`)
- Local verification prevents expensive re-runs of failed code

### Quality Constraints
- **TDD Enforcement**: New logic must include unit tests
- **No `Any` Types**: Strict type checking; no escape hatches
- **Linter Zero Tolerance**: `ruff check` must pass with 0 warnings
- **Public API Documentation**: All public functions require docstrings

## External Dependencies

### Google Jules API
- **Endpoint**: `https://jules.googleapis.com/v1alpha`
- **Authentication**: GCP service account or user OAuth token
- **Key Operations**:
  - `POST /sessions` - Create new coding task
  - `GET /sessions/{id}` - Poll status
  - `POST /sessions/{id}:approvePlan` - Bypass approval gate
  - `GET /sessions/{id}/activities` - Retrieve agent logs

### OpenSpec CLI
- **Package**: `@fission-ai/openspec` (Node.js, installed globally)
- **Minimum Version**: Latest (install via `npm install -g @fission-ai/openspec@latest`)
- **Commands Used**:
  - `openspec proposal` - Scaffold new change
  - `openspec validate` - Verify schema compliance
  - `openspec apply` - Trigger implementation
  - `openspec archive` - Merge specs and archive change

### Git Operations
- Project requires git 2.30+ for advanced diff and patch operations
- Synchronizer component relies on `git apply`, `git fetch`, `git cherry-pick`

### Optional Integrations
- **Ralph**: Shell wrapper for Claude Code autonomous loops (if using Claude integration)
- **GitHub API**: For automated PR creation and issue triage (future enhancement)
