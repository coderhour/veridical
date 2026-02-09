## 1. Report Generator Module
- [ ] 1.1 Create `src/veridical/report/` module with `__init__.py`
- [ ] 1.2 Implement `ReportGenerator` class that parses work log JSONL files
- [ ] 1.3 Implement `RunSummary` model with per-iteration breakdown and aggregate metrics
- [ ] 1.4 Calculate aggregate metrics: total duration, iteration count, success/failure rate, most-failed gates

## 2. Output Formatters
- [ ] 2.1 Implement `TerminalFormatter` using Rich tables for CLI display
- [ ] 2.2 Implement `JsonFormatter` for machine-readable output
- [ ] 2.3 Implement `HtmlFormatter` for single-file HTML report with embedded CSS
- [ ] 2.4 Include per-iteration detail: duration, gates run, gates failed, feedback excerpt

## 3. Cost Tracking
- [ ] 3.1 Add `cost_metadata` fields to `WorkLogEntry`: `api_calls_count`, `estimated_tokens`, `vm_time_seconds`
- [ ] 3.2 Populate cost fields in supervisor loop during iteration logging
- [ ] 3.3 Include cost summary in report output (total API calls, total estimated cost)

## 4. Pattern Detection
- [ ] 4.1 Implement gate failure frequency analysis across iterations
- [ ] 4.2 Detect gates that fail on first iteration but pass on retry (prompt improvement candidates)
- [ ] 4.3 Detect stagnation patterns (same gate failing repeatedly with same error)
- [ ] 4.4 Include pattern insights in report output

## 5. CLI Integration
- [ ] 5.1 Add `veri report` command with optional `--date` or `--run-id` filter
- [ ] 5.2 Support `--format` flag: `terminal` (default), `json`, `html`
- [ ] 5.3 Support `--output` flag for writing report to file
- [ ] 5.4 Add `veri report --list` to show available runs

## 6. Configuration
- [ ] 6.1 Add `report` section to config with `default_format` and `html_template` options
- [ ] 6.2 Update `.veridical.yaml.template` with report configuration examples

## 7. Testing
- [ ] 7.1 Add unit tests for `ReportGenerator` with sample JSONL data
- [ ] 7.2 Add unit tests for each output formatter
- [ ] 7.3 Add unit tests for pattern detection logic
- [ ] 7.4 Add integration test: run supervisor → generate report → verify report content

## 8. Documentation
- [ ] 8.1 Update README with report command usage and examples
- [ ] 8.2 Add sample report output screenshots or examples to documentation
