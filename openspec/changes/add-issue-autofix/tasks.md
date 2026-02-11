## 1. Intake Module
- [x] 1.1 Create `src/veridical/intake/__init__.py` with module exports
- [x] 1.2 Implement `IssueFetcher` class in `src/veridical/intake/fetcher.py` (GitHub API client for issues)
- [x] 1.3 Implement `TriageClassifier` in `src/veridical/intake/triage.py` (classify issue as bug/feature/question, estimate complexity)
- [x] 1.4 Implement `TaskGenerator` in `src/veridical/intake/task_generator.py` (convert issue + triage into task description for worker)
- [x] 1.5 Implement `PRPublisher` in `src/veridical/intake/publisher.py` (create GitHub PR with verification evidence)

## 2. Configuration
- [x] 2.1 Add `HealConfig` model to `src/veridical/config/schema.py` with GitHub token ref, triage settings, auto-PR toggle
- [x] 2.2 Add `heal: HealConfig` field to `VeridicalConfig`
- [x] 2.3 Add `heal` section to `.veridical.yaml.template` with documented options
- [x] 2.4 Add unit tests for `HealConfig` validation

## 3. CLI Command
- [x] 3.1 Create `src/veridical/cli/heal.py` with `veri heal` Typer command
- [x] 3.2 Implement `--repo` and `--issue` options for single-issue mode
- [x] 3.3 Implement `--watch` flag for continuous webhook/polling mode
- [x] 3.4 Implement `--auto-spec` flag for auto-generating OpenSpec proposals
- [x] 3.5 Implement `--dry-run` flag to show what would happen without executing
- [x] 3.6 Register `heal` command in main CLI app

## 4. Integration with Supervisor
- [x] 4.1 Wire intake pipeline output into `Supervisor.run()` task_description parameter
- [x] 4.2 Wire intake pipeline output into `LocalSupervisor.run()` for local mode
- [x] 4.3 On success, invoke `PRPublisher` to create PR with issue link and verification report
- [x] 4.4 On failure, post a comment on the issue with diagnostic summary

## 5. Tests
- [x] 5.1 Unit tests for `IssueFetcher` with mocked GitHub API responses
- [x] 5.2 Unit tests for `TriageClassifier` with sample issue bodies
- [x] 5.3 Unit tests for `TaskGenerator` output format
- [x] 5.4 Unit tests for `PRPublisher` with mocked GitHub API
- [x] 5.5 Integration test: full heal pipeline with mock worker (issue -> task -> verify -> PR)
- [x] 5.6 Integration test: `veri heal --dry-run` output validation
