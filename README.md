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

# Override the target branch for merging (default: auto-created from spec/task)
veri run "Fix login bug" --target-branch bugfix/login-correction
veri run "Fix login bug" -b bugfix/login-correction
```

### Local Mode (Agent Supervision)

Veridical can supervise local agents or scripts, not just Jules. This is useful for testing agents, running local repair scripts, or developing your own AI tools.

```bash
# Run a local agent script in a verify-and-fix loop
veri local "Fix the bug" --worker "./agent.py fix"

# Run an interactive shell command
veri local "Refactor code" --worker "python refactor.py" --max-iterations 5
```

**How it works:**
1. Veridical executes your worker command.
2. It runs your configured quality gates (tests, linters).
3. If gates fail, it feeds the error context back to the worker via the `VERIDICAL_ERROR_CONTEXT` environment variable.
4. It repeats until the gates pass or max iterations is reached.

**Configuration:**
```yaml
local:
  worker_command: "./my-agent.py"
  worker_timeout: 600
  mode: subprocess  # or "interactive"
  error_env_var: AGENT_ERROR_CONTEXT
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

#### Workflow Isolation (Branch Strategy)

Veridical is "safe by default." It avoids merging directly to your protected `main` branch.

**How it works:**
1. **Starting Branch Capture:** When you run `veri run`, it remembers which branch you're currently on.
2. **Work Branch Creation:** It creates a dedicated work branch based on your `base_branch` (default: `main`):
   - `feat/<sanitized-spec-name>` (e.g., `feat/add-user-auth`)
   - `fix/<sanitized-task-name>` (e.g., `fix/fix-login-bug`)
3. **Iteration Branches:** All AI progress happens in isolation branches (`veridical/iter-N`) branched from the work branch.
4. **Final Merge:** Once verification passes, changes are merged into the **work branch**, NOT your original starting branch.
5. **Auto-Return:** You are automatically checked out back to your starting branch when the loop finished.

**Configuration:**
You can disable this behavior to merge directly to your `base_branch` (legacy behavior):
```yaml
git:
  auto_create_work_branch: false
```

**Manual Override:**
Use `--target-branch` or `-b` to specify an exact branch to merge into.


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

### Parallel Quality Gates

Veridical supports running quality gates in parallel to significantly reduce verification time. Gates marked with `parallel: true` will be grouped and executed concurrently.

**Example configuration:**

```yaml
verifier:
  parallel_timeout: 600  # Maximum time for parallel batch execution
  quality_gates:
    # Sequential gate (runs first)
    - name: task_completion
      type: task_completion
      path: "auto"
      required: true

    # Parallel gates (run concurrently)
    - name: pytest
      command: pytest
      timeout: 300
      required: true
      parallel: true

    - name: ruff
      command: ruff check src/
      timeout: 60
      required: true
      parallel: true

    - name: mypy
      command: mypy src/
      timeout: 120
      required: true
      parallel: true
```

**Benefits:**
- **50-70% faster verification**: Independent tools like `pytest`, `ruff`, and `mypy` run simultaneously
- **Fail-fast behavior**: If a required gate fails, remaining parallel gates are cancelled immediately
- **Flexible grouping**: Mix sequential and parallel gates as needed

**How it works:**
1. Gates are grouped into batches based on the `parallel` flag
2. Sequential gates run in their own batch (one at a time)
3. Consecutive parallel gates are grouped and run concurrently using `asyncio.gather()`
4. If a required gate fails, the batch is cancelled and verification stops

### Environment Variables

Set your Jules API key:

```bash
export JULES_API_KEY="your-api-key-here"
```

### Work Log

Veridical automatically records detailed logs of each iteration to help you audit and debug autonomous runs. Work logs are organized by date and stored in the `worklog/` directory (alongside `.veridical.yaml`).

**What's logged:**
- **Inputs**: Task description, error context from previous iteration, prompt sent to Jules
- **Outputs**: Session status, verification results, error summaries, iteration duration
- **Metadata**: Timestamp, iteration number, session ID

**Log format:**
```
worklog/
└── YYYY-MM-DD/
    └── iterations.jsonl  # One JSON object per line
```

**Example entry:**
```json
{
  "timestamp": "2026-02-06T15:30:00",
  "iteration": 1,
  "session_id": "session-abc-123",
  "task_description": "Implement user authentication",
  "error_context": null,
  "prompt_sent": "Implement JWT-based authentication",
  "session_status": "completed",
  "verification_passed": true,
  "verification_errors": null,
  "duration_seconds": 180.5
}
```

**Configuration:**
```yaml
worklog:
  enabled: true           # Enable/disable work log (default: true)
  directory: worklog      # Directory name (default: "worklog")
```

**Disable work logs:**
```yaml
worklog:
  enabled: false
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

Veridical uses a **Control Loop Architecture** with a pluggable **Worker** abstraction:

1. **Supervisor**: Orchestrates the entire loop (IDLE → DISPATCHING → POLLING → SYNCING → VERIFYING)
2. **Worker** (protocol): Pluggable backend interface with three methods — `dispatch()`, `poll()`, `sync()`
   - **JulesWorker**: Default implementation wrapping Dispatcher, Poller, and Synchronizer for Google Jules
3. **Verifier**: Runs quality gates and generates feedback
4. **WorkerRegistry**: Maps backend names (e.g. `jules`, `local`) to Worker implementations

The Worker protocol decouples the Supervisor from any specific AI backend, enabling alternative workers (local scripts, other AI services) without modifying the core loop.

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
