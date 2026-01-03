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
veridical fix "Fix the login validation bug"

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
```

## License

MIT
