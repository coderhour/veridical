# Implementation Tasks

## Phase 1: Project Infrastructure ✅

### 1.1 Project Configuration ✅
- [x] 1.1.1 Create `pyproject.toml` with project metadata and dependencies
- [x] 1.1.2 Configure `ruff` for linting and formatting in `pyproject.toml`
- [x] 1.1.3 Configure `mypy` for strict type checking in `pyproject.toml`
- [x] 1.1.4 Configure `pytest` with coverage settings in `pyproject.toml`
- [x] 1.1.5 Create `.python-version` file specifying Python 3.11+
- [x] 1.1.6 Run `uv sync` to verify dependency resolution

### 1.2 Package Structure ✅
- [x] 1.2.1 Create `src/veridical/__init__.py` with version export
- [x] 1.2.2 Create `src/veridical/__main__.py` for `python -m veridical`
- [x] 1.2.3 Create `src/veridical/py.typed` marker for PEP 561
- [x] 1.2.4 Create placeholder `__init__.py` files for all subpackages

### 1.3 Testing Infrastructure ✅
- [x] 1.3.1 Create `tests/` directory structure (unit, integration, e2e)
- [x] 1.3.2 Create `tests/conftest.py` with shared fixtures
- [x] 1.3.3 Create `tests/unit/conftest.py` with unit test fixtures
- [x] 1.3.4 Add placeholder tests to verify pytest discovery
- [x] 1.3.5 Verify `pytest` runs and discovers tests (81 tests passing)

---

## Phase 2: Core Models and Exceptions ✅

### 2.1 Exception Hierarchy ✅
- [x] 2.1.1 Create `src/veridical/exceptions.py` with base `VeridicalError`
- [x] 2.1.2 Add `ConfigurationError`, `APIError`, `SynchronizationError`
- [x] 2.1.3 Add `VerificationError`, `CircuitOpenError`, `RateLimitError`
- [x] 2.1.4 Write unit tests for exception hierarchy

### 2.2 Core Data Models ✅
- [x] 2.2.1 Create `src/veridical/models/__init__.py`
- [x] 2.2.2 Create `src/veridical/models/session.py` with `SessionInfo`, `SessionState`
- [x] 2.2.3 Create `src/veridical/models/iteration.py` with `IterationContext`
- [x] 2.2.4 Create `src/veridical/models/result.py` with `LoopResult`, `VerificationResult`, `GateResult`, `PatchResult`
- [x] 2.2.5 Write unit tests for model serialization/validation

---

## Phase 3: Configuration System ✅

### 3.1 Config Schema ✅
- [x] 3.1.1 Create `src/veridical/config/__init__.py`
- [x] 3.1.2 Create `src/veridical/config/schema.py` with Pydantic settings models
- [x] 3.1.3 Define `JulesConfig`, `SupervisorConfig`, `VerifierConfig`, `GitConfig` submodels
- [x] 3.1.4 Define `VeridicalConfig` root model combining all sections
- [x] 3.1.5 Define `QualityGate` model for verifier commands

### 3.2 Config Loading ✅
- [x] 3.2.1 Create `src/veridical/config/defaults.py` with default values
- [x] 3.2.2 Create `src/veridical/config/loader.py` with `load_config()` function
- [x] 3.2.3 Implement YAML file discovery and loading
- [x] 3.2.4 Implement environment variable override logic
- [x] 3.2.5 Implement config validation with clear error messages
- [x] 3.2.6 Write unit tests for config loading scenarios

### 3.3 Config Template ✅
- [x] 3.3.1 Create `.veridical.yaml.template` with documented options
- [x] 3.3.2 Add function to generate template in `loader.py`

---

## Phase 4: API Client ✅

### 4.1 API Models ✅
- [x] 4.1.1 Create `src/veridical/api/__init__.py`
- [x] 4.1.2 Create `src/veridical/api/models.py` with request/response Pydantic models
- [x] 4.1.3 Define `CreateSessionRequest`, `SourceContext`, `GitHubRepoContext`
- [x] 4.1.4 Define `SessionResponse`, `ActivityEntry` response models
- [x] 4.1.5 Define `SessionState`, `AutomationMode` enums

### 4.2 API Exceptions ✅
- [x] 4.2.1 Create `src/veridical/api/exceptions.py`
- [x] 4.2.2 Define `APIError`, `RateLimitError`, `AuthenticationError`

### 4.3 HTTP Client ✅
- [x] 4.3.1 Create `src/veridical/api/client.py` with `JulesClient` class
- [x] 4.3.2 Implement async context manager (`__aenter__`, `__aexit__`)
- [x] 4.3.3 Implement `create_session()` method
- [x] 4.3.4 Implement `get_session()` method
- [x] 4.3.5 Implement `approve_plan()` method
- [x] 4.3.6 Implement `send_message()` method
- [x] 4.3.7 Implement `get_activities()` method
- [x] 4.3.8 Implement retry logic with exponential backoff
- [x] 4.3.9 Write unit tests using `respx` for HTTP mocking

---

## Phase 5: Component Interfaces ✅

### 5.1 Supervisor Interface ✅
- [x] 5.1.1 Create `src/veridical/supervisor/__init__.py`
- [x] 5.1.2 Create `src/veridical/supervisor/state.py` with `SupervisorState` enum
- [x] 5.1.3 Create `src/veridical/supervisor/circuit_breaker.py` with `CircuitBreaker` interface
- [x] 5.1.4 Create `src/veridical/supervisor/loop.py` with `Supervisor` class skeleton
- [x] 5.1.5 Define `run()` method signature (async, returns `LoopResult`)
- [x] 5.1.6 Write unit tests for state transitions

### 5.2 Dispatcher Interface ✅
- [x] 5.2.1 Create `src/veridical/dispatcher/__init__.py`
- [x] 5.2.2 Create `src/veridical/dispatcher/prompt.py` with prompt builder
- [x] 5.2.3 Create `src/veridical/dispatcher/session.py` with `Dispatcher` class
- [x] 5.2.4 Define `build_prompt()` method signature
- [x] 5.2.5 Define `create_session()` method signature
- [x] 5.2.6 Create `src/veridical/dispatcher/agents_md.py` with constraint injection
- [x] 5.2.7 Write unit tests for prompt construction

### 5.3 Poller Interface ✅
- [x] 5.3.1 Create `src/veridical/poller/__init__.py`
- [x] 5.3.2 Create `src/veridical/poller/backoff.py` with backoff strategy
- [x] 5.3.3 Create `src/veridical/poller/monitor.py` with `Poller` class
- [x] 5.3.4 Define `wait_for_completion()` method signature
- [x] 5.3.5 Write unit tests for backoff calculation

### 5.4 Synchronizer Interface ✅
- [x] 5.4.1 Create `src/veridical/synchronizer/__init__.py`
- [x] 5.4.2 Create `src/veridical/synchronizer/git.py` with Git wrapper
- [x] 5.4.3 Create `src/veridical/synchronizer/branch.py` with branch operations
- [x] 5.4.4 Create `src/veridical/synchronizer/patch.py` with patch application
- [x] 5.4.5 Define `Synchronizer` class with method signatures
- [x] 5.4.6 Write unit tests using temporary git repos

### 5.5 Verifier Interface ✅
- [x] 5.5.1 Create `src/veridical/verifier/__init__.py`
- [x] 5.5.2 Create `src/veridical/verifier/runner.py` with command execution
- [x] 5.5.3 Create `src/veridical/verifier/feedback.py` with error summarization
- [x] 5.5.4 Create `src/veridical/verifier/quality_gate.py` with `Verifier` class
- [x] 5.5.5 Define `run_all()` and `run_gate()` method signatures
- [x] 5.5.6 Write unit tests for command execution

---

## Phase 6: CLI Implementation ✅

### 6.1 CLI Framework ✅
- [x] 6.1.1 Create `src/veridical/cli/__init__.py`
- [x] 6.1.2 Create `src/veridical/cli/main.py` with Typer app
- [x] 6.1.3 Add `--version` callback
- [x] 6.1.4 Add `--verbose` global option

### 6.2 CLI Commands ✅
- [x] 6.2.1 Create `src/veridical/cli/fix.py` with `fix` command skeleton
- [x] 6.2.2 Create `src/veridical/cli/verify.py` with `verify` command
- [x] 6.2.3 Create `src/veridical/cli/status.py` with `status` command skeleton
- [x] 6.2.4 Create `src/veridical/cli/config.py` with `config` subcommands
- [x] 6.2.5 Register all commands in `main.py`

### 6.3 CLI Validation ✅
- [x] 6.3.1 Verify `veridical --help` works
- [x] 6.3.2 Verify `veridical --version` works
- [x] 6.3.3 Verify all subcommand help displays
- [ ] 6.3.4 Write integration tests for CLI invocation

---

## Phase 7: Final Validation

### 7.1 Quality Gates ✅
- [x] 7.1.1 Run `ruff check src/` and fix any issues (All checks passed!)
- [x] 7.1.2 Run `ruff format src/ tests/` to format code (6 files reformatted)
- [x] 7.1.3 Run `mypy src/` and fix any type errors (Success: no issues found)
- [x] 7.1.4 Run `pytest --cov=src/veridical` and verify coverage (61% coverage, 81 tests passing)

### 7.2 Documentation
- [ ] 7.2.1 Add docstrings to all public classes and functions (Most already have docstrings)
- [x] 7.2.2 Verify `veridical --help` output is clear and complete

### 7.3 Final Checks
- [x] 7.3.1 Verify `uv sync` completes without errors
- [x] 7.3.2 Verify `uv run veridical --version` works
- [ ] 7.3.3 Test installation in fresh virtual environment

---

## Dependencies

- **Phase 2** depends on **Phase 1** (package structure must exist)
- **Phase 3** depends on **Phase 2** (models used in config)
- **Phase 4** depends on **Phase 2, 3** (models and config needed)
- **Phase 5** depends on **Phase 2, 3, 4** (all foundational pieces)
- **Phase 6** depends on **Phase 3, 5** (config and components)
- **Phase 7** depends on all previous phases

## Parallelization Opportunities

Within each phase, many tasks can be parallelized:
- In Phase 2: Exception and model development can proceed in parallel
- In Phase 3: Schema and loading logic are sequential, but tests can follow each
- In Phase 5: All five component interfaces can be developed in parallel
- In Phase 6: All CLI commands can be developed in parallel after framework setup
