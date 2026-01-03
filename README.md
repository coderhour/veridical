# Veridical

Local Supervisory Control System for Google Jules - autonomous quality assurance loops.

## Overview

Veridical implements autonomous quality assurance loops that enforce high code quality through iterative testing, linting, and spec-driven development. It acts as a supervisory layer between your local development environment and Google Jules, ensuring that generated code meets your project's quality standards.

## Installation

```bash
uv add veridical
```

## Quick Start

```bash
# Initialize configuration
veridical config init

# Run quality verification locally
veridical verify

# Start an autonomous fix loop
veridical run "Fix the login validation bug"

# Check status of active sessions
veridical status
```

## Configuration

Create a `.veridical.yaml` file in your project root:

```yaml
jules:
  api_base_url: https://jules.googleapis.com/v1alpha
  poll_interval: 30
  poll_timeout: 3600
  auto_approve_plans: true

supervisor:
  max_iterations: 10
  max_consecutive_failures: 3
  stagnation_threshold: 3

verifier:
  quality_gates:
    - name: pytest
      command: pytest
    - name: ruff
      command: ruff check src/
    - name: mypy
      command: mypy src/

git:
  base_branch: main
  branch_prefix: veridical/iter-
```

### Environment Variables

Set your Jules API key:

```bash
export JULES_API_KEY="your-api-key-here"
```

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

## License

MIT
