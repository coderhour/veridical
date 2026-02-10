## 1. Report Generator Module
- [x] 1.1 Create `src/veridical/report/` module with `__init__.py`
- [x] 1.2 Implement `ReportGenerator` class that parses work log JSONL files
- [x] 1.3 Implement `RunSummary` model with per-iteration breakdown and aggregate metrics
- [x] 1.4 Calculate aggregate metrics: total duration, iteration count, success/failure rate, most-failed gates

## 2. Output Formatters
- [x] 2.1 Implement `TerminalFormatter` using Rich tables for CLI display
- [x] 2.2 Implement `JsonFormatter` for machine-readable output
- [x] 2.3 Implement `HtmlFormatter` for single-file HTML report with embedded CSS
- [x] 2.4 Include per-iteration detail: duration, gates run, gates failed, feedback excerpt

## 3. Cost Tracking
- [x] 3.1 Add `cost_metadata` fields to `WorkLogEntry`: `api_calls_count`, `estimated_tokens`, `vm_time_seconds`
- [x] 3.2 Populate cost fields in supervisor loop during iteration logging
- [x] 3.3 Include cost summary in report output (total API calls, total estimated cost)

## 4. Pattern Detection
- [x] 4.1 Implement gate failure frequency analysis across iterations
- [x] 4.2 Detect gates that fail on first iteration but pass on retry (prompt improvement candidates)
- [x] 4.3 Detect stagnation patterns (same gate failing repeatedly with same error)
- [x] 4.4 Include pattern insights in report output

## 5. CLI Integration
- [x] 5.1 Add `veri report` command with optional `--date` or `--run-id` filter
- [x] 5.2 Support `--format` flag: `terminal` (default), `json`, `html`
- [x] 5.3 Support `--output` flag for writing report to file
- [x] 5.4 Add `veri report --list` to show available runs

## 6. Configuration
- [x] 6.1 Add `report` section to config with `default_format` and `html_template` options
- [x] 6.2 Update `.veridical.yaml.template` with report configuration examples

## 7. Testing
- [x] 7.1 Add unit tests for `ReportGenerator` with sample JSONL data
- [x] 7.2 Add unit tests for each output formatter
- [x] 7.3 Add unit tests for pattern detection logic
- [x] 7.4 Add integration test: run supervisor → generate report → verify report content

## 8. Documentation
- [x] 8.1 Update README with report command usage and examples
- [x] 8.2 Add sample report output screenshots or examples to documentation
