# Migration Guide: v0.2.0 (Worker Abstraction)

## Overview

Version 0.2.0 introduces a major architectural change: the **Worker Abstraction**. This decouples the `Supervisor` from the specific implementation of the AI agent (previously hardcoded to `JulesClient`).

## Breaking Changes

### 1. Supervisor Constructor

The `Supervisor` class constructor has changed signature.

**Old (v0.1.x):**
```python
class Supervisor:
    def __init__(
        self,
        config: "VeridicalConfig",
        client: JulesClient,  # <-- DIRECT CLIENT
        repo_path: Path,
        *,
        verbose: bool = False,
        console: Console | None = None,
    )
```

**New (v0.2.0):**
```python
class Supervisor:
    def __init__(
        self,
        config: "VeridicalConfig",
        worker: Worker,      # <-- ABSTRACT WORKER
        repo_path: Path,
        *,
        verbose: bool = False,
        console: Console | None = None,
    )
```

### 2. Configuration Schema

The `VeridicalConfig` now includes a `worker` section.

**New Config Structure:**
```yaml
worker:
  backend: "jules"  # Default
```

## Migration Steps

If you are using Veridical programmatically:

1.  **Import the Registry**:
    ```python
    from veridical.worker.registry import WorkerRegistry
    ```

2.  **Create a Worker**:
    Instead of passing `client` directly to `Supervisor`, create a worker first.
    ```python
    # Old
    # supervisor = Supervisor(config, client, path)

    # New
    worker = WorkerRegistry.create_worker(
        config,
        client=client,  # Pass client if using 'jules' backend
        repo_path=path,
        console=console
    )
    supervisor = Supervisor(config, worker, path)
    ```

If you are using the CLI:

- No changes required. The CLI automatically handles the new configuration and defaults to `jules` backend.
