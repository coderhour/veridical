## 1. Diagnose Module
- [ ] 1.1 Create `src/veridical/diagnose/__init__.py` with module exports
- [ ] 1.2 Implement `StackTraceParser` in `src/veridical/diagnose/stack_trace.py` (extract file:line references from Python/generic tracebacks)
- [ ] 1.3 Implement `CallGraphAnalyzer` in `src/veridical/diagnose/call_graph.py` (trace from crash site to root cause using AST/tree-sitter)
- [ ] 1.4 Implement `BlameCorrelator` in `src/veridical/diagnose/blame.py` (identify recent changes to crash-site code via git blame)
- [ ] 1.5 Implement `Localizer` in `src/veridical/diagnose/localizer.py` (orchestrates all signals into a ranked `LocalizationReport`)

## 2. Feedback Integration
- [ ] 2.1 Extend `FeedbackGenerator.generate_feedback()` in `src/veridical/verifier/feedback.py` to accept an optional `Localizer` instance
- [ ] 2.2 When localizer is available, enrich gate failure feedback with file:line localization data
- [ ] 2.3 Format enriched feedback as: "Root cause likely in {file}:{line} ({reason})"

## 3. Supervisor Integration
- [ ] 3.1 In `Supervisor.run()`, optionally run localization on the initial task description if it contains error/stacktrace patterns
- [ ] 3.2 In `Supervisor.run()`, run localization on `error_context` before dispatching retry iterations
- [ ] 3.3 In `LocalSupervisor.run()`, apply same localization enrichment to error context

## 4. CLI Command
- [ ] 4.1 Create `src/veridical/cli/diagnose.py` with `veri diagnose` Typer command
- [ ] 4.2 Accept input via: `--error "traceback text"`, `--test "test_name"`, or `--file path/to/logfile`
- [ ] 4.3 Display localization report with ranked file:line candidates and confidence scores
- [ ] 4.4 Register `diagnose` command in main CLI app

## 5. Tests
- [ ] 5.1 Unit tests for `StackTraceParser` with Python traceback samples
- [ ] 5.2 Unit tests for `BlameCorrelator` with mock git blame output
- [ ] 5.3 Unit tests for `Localizer` ranking and report generation
- [ ] 5.4 Integration test: localization enriches feedback in verify loop
- [ ] 5.5 Integration test: `veri diagnose` CLI output with sample error input
