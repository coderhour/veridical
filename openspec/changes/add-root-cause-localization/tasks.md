## 1. Diagnose Module
- [x] 1.1 Create `src/veridical/diagnose/__init__.py` with module exports
- [x] 1.2 Implement `StackTraceParser` in `src/veridical/diagnose/stack_trace.py` (extract file:line references from Python/generic tracebacks)
- [x] 1.3 Implement `CallGraphAnalyzer` in `src/veridical/diagnose/call_graph.py` (trace from crash site to root cause using AST)
- [x] 1.4 Implement `BlameCorrelator` in `src/veridical/diagnose/blame.py` (identify recent changes to crash-site code via git blame)
- [x] 1.5 Implement `Localizer` in `src/veridical/diagnose/localizer.py` (orchestrates all signals into a ranked `LocalizationReport`)
- [x] 1.6 Update `CallGraphAnalyzer.find_callers()` signature to remove unused `target_file` parameter and update call sites/tests

## 2. Feedback Integration
- [x] 2.1 Extend `FeedbackGenerator.generate_feedback()` in `src/veridical/verifier/feedback.py` to accept an optional `Localizer` instance
- [x] 2.2 When localizer is available, enrich gate failure feedback with file:line localization data
- [x] 2.3 Format enriched feedback as: "Root cause likely in {file}:{line} ({reason})"

## 3. Supervisor Integration
- [x] 3.1 In `Supervisor.run()`, optionally run localization on the initial task description if it contains error/stacktrace patterns
- [x] 3.2 In `Supervisor.run()`, run localization on `error_context` before dispatching retry iterations
- [x] 3.3 In `LocalSupervisor.run()`, apply same localization enrichment to error context

## 4. CLI Command
- [x] 4.1 Create `src/veridical/cli/diagnose.py` with `veri diagnose` Typer command
- [x] 4.2 Accept input via: `--error "traceback text"`, `--test "test_name"`, or `--file path/to/logfile`
- [x] 4.3 Display localization report with ranked file:line candidates and confidence scores
- [x] 4.4 Register `diagnose` command in main CLI app

## 5. Tests
- [x] 5.1 Unit tests for `StackTraceParser` with Python traceback samples
- [x] 5.2 Unit tests for `BlameCorrelator` with mock git blame output
- [x] 5.3 Unit tests for `Localizer` ranking and report generation
- [x] 5.4 Integration test: localization enriches feedback in verify loop
- [x] 5.5 Integration test: `veri diagnose` CLI output with sample error input
