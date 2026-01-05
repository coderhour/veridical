# Veridical

Local Supervisory Control System for Google Jules - autonomous quality assurance loops.

## Overview

Veridical implements autonomous quality assurance loops that enforce high code quality through iterative testing, linting, and spec-driven development. It acts as a supervisory layer between your local development environment and Google Jules, ensuring that generated code meets your project's quality standards.

## Installation

### Prerequisites

Veridical requires the following tools to be installed on your system:

1.  **Git**: For repository management and patch application.
2.  **OpenSpec CLI**: For spec-driven development and proposal management.
    ```bash
    npm install -g @fission-ai/openspec@latest
    ```
3.  **Python 3.11+**: The core execution environment.
4.  **uv** (Recommended): For fast and reliable dependency management.

### For Development

Clone the repository and install with uv:

```bash
git clone https://github.com/coderhour/veridical.git
cd veridical
uv sync --all-extras
```

### For Users (Global Installation)

Once published to PyPI, install Veridical globally as a CLI tool:

#### Recommended: Using `uv` (Fast & Isolated)

```bash
# Install globally
uv tool install veridical

# Update to latest version
uv tool upgrade veridical

# Uninstall
uv tool uninstall veridical
```

#### Alternative: Using `pipx` (Also Good)

```bash
# Install globally
pipx install veridical

# Update
pipx upgrade veridical

# Uninstall
pipx uninstall veridical
```

#### Traditional: Using `pip` (Not Recommended)

```bash
# System-wide install (may require sudo)
pip install veridical

# User-level install (no sudo needed)
pip install --user veridical
```

**Note**: `uv tool` and `pipx` are recommended because they install CLI tools in isolated environments, avoiding dependency conflicts.

### For Project Dependencies

To add Veridical as a project dependency:

```bash
# With uv
uv add veridical

# With pip
pip install veridical
```

## Quick Start: End-to-End Example

Veridical works best when combined with **OpenSpec**. Here is how you use them together to autonomously fix a bug.

### 1. Create a Change Proposal
First, design your change. The AI assistant (Antigravity, Claude, etc.) acts as an architect to draft your plan.

```bash
# Use the slash command: /openspec-proposal "Fix password validation bug"
```

**What happens:** Your AI assistant analyzes the codebase and generates **full content** (not just a skeleton) in `openspec/changes/fix-password-validation/`:
- `proposal.md`: Comprehensive rationale and impact analysis.
- `tasks.md`: A step-by-step technical implementation checklist.
- `specs/`: Specific requirement deltas (ADDED/MODIFIED/REMOVED).

**Critical Step:** Review and refine the AI's draft. Once satisfied, you **must commit and push** these files so Google Jules can read them from GitHub:

```bash
git add openspec/changes/fix-password-validation/
git commit -m "docs: add proposal for password validation fix"
git push origin main
```

### 2. Run the Autonomous Loop
Once the proposal is on GitHub, let Veridical orchestrate the implementation and verification.

```bash
# Start the autonomous supervisor
veri run "Fix password validation per approved proposal"
```

### 3. What Veridical Does (The Magic)
Veridical manages the entire lifecycle so you don't have to:
- **Dispatches**: Sends the task and OpenSpec context to **Google Jules**.
- **Monitors**: Polls Jules for completion (runs in the cloud, doesn't block your machine).
- **Synchronizes**: Downloads the generated **patch (git diff)** via the API and applies it to a fresh local isolation branch. No remote push required.
- **Verifies**: Runs quality gates defined in your `.veridical.yaml`. Since these are just CLI commands (e.g., `pytest`, `npm test`, `go test`), Veridical works with any language or framework.
- **Iterates**: If a gate fails, it sends the exact error back to Jules and retries.
- **Completion**: Once all gates pass locally, it merges the fixed, tested, and linted code.

### 4. Archive and Baseline
Finally, archive the change to update your project's permanent specifications.

```bash
openspec archive fix-password-validation
```

---

### Command Reference

```bash
# Initialize configuration for a Python project (default)
veridical config init

# Initialize configuration for a Node.js project
veridical config init --template nodejs

# Start the autonomous supervisor (interactive spec selection if no task provided)
veri run

# Start with an explicit task (auto-matches OpenSpec if name included)
veri run "Implement spec add-dynamic-spec-detection"

# Skip OpenSpec task verification for bug fixes or ad-hoc work
veri run "Fix login validation bug" --no-spec
# Or use the shortcut:
veri run "Fix login validation bug" --skip-tasks

# Resume an existing Jules session
veri run "Continue the task" --session-id abc123def456

# Run quality verification locally
# (Runs pytest, ruff, etc. defined in .veridical.yaml)
veri verify

# Check status of active sessions
veri status
```

#### Session Resumption

The `--session-id` / `-s` option allows you to resume an existing Jules session instead of creating a new one. This is useful when:

- A session was interrupted (network failure, timeout, user abort)
- A session completed but local verification failed and you want to retry
- You want to continue iterating on an existing session

**How it works:**
- On the first iteration, Veridical skips creating a new session and goes directly to polling the provided session ID
- If verification fails and the loop continues, subsequent iterations create new sessions as normal
- The session ID can be found in the output of `veri status` or from the Jules console

**Example:**
```bash
# Start a task
veri run "Implement user authentication"
# Session abc123 created...
# (interrupted or failed)

# Resume the same session later
veri run "Continue authentication implementation" -s abc123
```

## Configuration

Create a `.veridical.yaml` file in your project root using `veridical config init`. You can specify a template for your project's language:

```bash
# For Python (default)
veridical config init

# For Node.js
veridical config init --template nodejs

# For Elixir
veridical config init --template elixir

# For Java
veridical config init --template java

# For Go
veridical config init --template go

# For Rust
veridical config init --template rust

# For TypeScript
veridical config init --template typescript

# For Ruby
veridical config init --template ruby

# For PHP
veridical config init --template php

# For C#/.NET
veridical config init --template dotnet
```

This will generate a configuration file with sensible defaults for the chosen language.

### Supported Templates

| Template | Key Quality Gates |
| :--- | :--- |
| `python` | `pytest`, `ruff check`, `ruff format`, `mypy` |
| `nodejs` | `npm test`, `eslint`, `prettier` |
| `elixir` | `mix test`, `credo`, `mix format`, `dialyzer` |
| `java` | `gradlew test`, `checkstyle` |
| `go` | `go test`, `go vet`, `golangci-lint`, `gofmt` |
| `rust` | `cargo test`, `cargo clippy`, `cargo fmt` |
| `typescript` | `npm test`, `tsc`, `eslint`, `prettier` |
| `ruby` | `rspec`, `rubocop` |
| `php` | `phpunit`, `phpstan`, `php-cs-fixer` |
| `dotnet` | `dotnet test`, `dotnet format`, `dotnet build` |

### Environment Variables

Set your Jules API key:

```bash
export JULES_API_KEY="your-api-key-here"
```

## Development Workflow (OpenSpec)

Veridical uses **OpenSpec** for spec-driven development. This ensures that every significant change is well-defined, documented, and traceable.

### When to use OpenSpec
- Creating new features or significant components.
- Modifying core business logic or architectural patterns.
- Any change that requires multiple steps or coordination.

*Note: For simple bug fixes, typos, or documentation updates, direct edits are acceptable.*

### The OpenSpec Lifecycle

The workflow consists of three main stages, managed via slash commands or CLI:

1.  **Proposal (`/openspec-proposal`)**: 
    - **Purpose**: Design the change before implementing it.
    - **Actions**: Scaffolds `proposal.md`, `tasks.md`, and spec deltas in `openspec/changes/<change-id>/`.
    - **Goal**: Define *why*, *what*, and *how* (tasks) without writing code.

2.  **Implementation (`/openspec-apply`)**:
    - **Purpose**: Execute the approved plan.
    - **Actions**: Follows the `tasks.md` sequentially to implement the code.
    - **Goal**: Complete the feature and verify it against the specs.

3.  **Archiving (`/openspec-archive`)**:
    - **Purpose**: Merge the specs into the project foundation.
    - **Actions**: Merges spec deltas into `openspec/specs/` and moves the change to `openspec/changes/archive/`.
    - **Goal**: Maintain a clean "source of truth" for the project's capabilities.

### CLI Usage

If you prefer using the CLI directly:

```bash
# List all active changes
openspec list

# Validate your change
openspec validate <change-id> --strict

# Archive a completed change
openspec archive <change-id> --yes
```

For detailed instructions and conventions, refer to [openspec/AGENTS.md](./openspec/AGENTS.md).

## How Repo Detection Works

When you run `veridical run`, Veridical automatically detects your GitHub repository from the current directory's git remote:

1. **Auto-detection**: Veridical reads the git remote URL from your current repository
2. **Conversion**: Converts `git@github.com:owner/repo.git` → `sources/github/owner/repo`
3. **Session Creation**: Passes this to Jules API when creating a session

**Note**: The current scaffold implementation is a skeleton. Full repo detection will be implemented in the next phase. For now, you would need to:

```python
# Future implementation will auto-detect from:
# git remote get-url origin
# → git@github.com:veridical/veridical.git
# → sources/github/veridical/veridical
```

## Programmatic Usage

### Creating a Jules Session

```python
import asyncio
from pathlib import Path
from veridical.api.client import JulesClient
from veridical.dispatcher.session import Dispatcher
from veridical.config.loader import load_config

async def create_fix_session():
    # Load configuration
    config = load_config()
    
    # Create API client
    async with JulesClient(api_key="your-api-key") as client:
        # Create dispatcher
        dispatcher = Dispatcher(config, client)
        
        # Build prompt
        prompt = dispatcher.build_prompt(
            task="Fix the login validation bug",
            error_context=None  # Or error from previous iteration
        )
        
        # Create session
        session = await dispatcher.create_session(
            prompt=prompt,
            source="sources/github/veridical/veridical",  # Your repo
            branch="main"  # Optional, defaults to config.git.base_branch
        )
        
        print(f"Session created: {session.session_id}")
        print(f"State: {session.state}")

asyncio.run(create_fix_session())
```

### Running Quality Gates

```python
import asyncio
from pathlib import Path
from veridical.config.loader import load_config
from veridical.verifier.quality_gate import Verifier

async def run_verification():
    config = load_config()
    repo_path = Path.cwd()
    
    verifier = Verifier(config, repo_path)
    
    # Run all quality gates
    result = await verifier.run_all()
    
    if result.passed:
        print("✅ All quality gates passed!")
    else:
        print("❌ Some gates failed:")
        for gate in result.failed_gates:
            print(f"  - {gate.name}: {gate.error_output[:200]}")

asyncio.run(run_verification())
```

### Monitoring a Session

```python
import asyncio
from veridical.api.client import JulesClient
from veridical.poller.monitor import Poller
from veridical.config.loader import load_config

async def monitor_session(session_id: str):
    config = load_config()
    
    async with JulesClient(api_key="your-api-key") as client:
        poller = Poller(config, client)
        
        # Wait for completion (with timeout)
        result = await poller.wait_for_completion(
            session_id=session_id,
            timeout=3600  # 1 hour
        )
        
        print(f"Session completed in {result.duration_seconds:.1f}s")
        print(f"Final state: {result.final_state}")
        print(f"Poll attempts: {result.poll_count}")

asyncio.run(monitor_session("your-session-id"))
```

### Full Autonomous Loop (Future)

```python
import asyncio
from veridical.supervisor.loop import Supervisor
from veridical.config.loader import load_config

async def run_autonomous_loop():
    config = load_config()
    supervisor = Supervisor(config)
    
    # This will be implemented in the next phase
    result = await supervisor.run(
        task_description="Fix the login validation bug"
    )
    
    if result.success:
        print(f"✅ Task completed in {result.iterations} iterations")
    else:
        print(f"❌ Failed: {result.failure_reason}")

# asyncio.run(run_autonomous_loop())  # Not yet implemented
```

## Architecture

Veridical uses a **Control Loop Architecture** with five core components:

1. **Supervisor**: Orchestrates the entire loop (IDLE → DISPATCHING → POLLING → SYNCING → VERIFYING)
2. **Dispatcher**: Builds prompts and creates Jules sessions
3. **Poller**: Monitors session status with intelligent backoff
4. **Synchronizer**: Applies patches to local git branches
5. **Verifier**: Runs quality gates and generates feedback

## Development

```bash
# Install with dev dependencies
uv sync --all-extras

# Run tests
pytest

# Run linter
ruff check src/

# Run type checker
mypy src/

# Run all quality checks
pytest && ruff check src/ && mypy src/
```

## Project Status

**Current Phase**: Foundation Scaffold (Complete ✅)
- ✅ Package structure and configuration
- ✅ API client with retry logic
- ✅ Component interfaces defined
- ✅ CLI skeleton implemented
- ✅ 81 tests passing, 61% coverage
- ✅ All quality gates passing (ruff, mypy, pytest)

**Next Phase**: Business Logic Implementation
- [ ] Full supervisor loop implementation
- [ ] Git repo auto-detection
- [ ] Patch application and verification
- [ ] Error feedback generation
- [ ] End-to-end integration tests

## Pro-Tips & FAQ

### Do I always need an OpenSpec proposal?
No. For trivial fixes (typos, CSS tweaks, documentation), you can skip OpenSpec and run `veri run "your task"` directly. Veridical will still enforce your local quality gates (pytest, ruff, etc.).

### How does Veridical find my `tasks.md`?
Veridical scan `openspec/changes/*/tasks.md` for incomplete tasks. When you run `veri run`, it tries to match your task description to a spec name (e.g., "Implement spec <name>"). If it can't match or you didn't provide a description, it shows an interactive menu of all available specs with open tasks.

### Can I skip task verification?
Yes. Use the `--no-spec` or `--skip-tasks` flag if you're doing work that doesn't have an OpenSpec proposal (like a simple bug fix).

### Does Veridical work with other languages?
Yes! While Veridical itself is written in Python, you can configure any command in `.veridical.yaml`. You can use it to supervise Go, Rust, JavaScript, or any project with a CLI-based test suite.

## License

MIT
