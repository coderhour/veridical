## 1. Intake Module
- [ ] 1.1 Create `src/veridical/intake/__init__.py` with module exports
- [ ] 1.2 Implement `IssueFetcher` class in `src/veridical/intake/fetcher.py` (GitHub API client for issues)
- [ ] 1.3 Implement `TriageClassifier` in `src/veridical/intake/triage.py` (classify issue as bug/feature/question, estimate complexity)
- [ ] 1.4 Implement `TaskGenerator` in `src/veridical/intake/task_generator.py` (convert issue + triage into task description for worker)
- [ ] 1.5 Implement `PRPublisher` in `src/veridical/intake/publisher.py` (create GitHub PR with verification evidence)

## 2. Configuration
- [ ] 2.1 Add `HealConfig` model to `src/veridical/config/schema.py` with GitHub token ref, triage settings, auto-PR toggle
- [ ] 2.2 Add `heal: HealConfig` field to `VeridicalConfig`
- [ ] 2.3 Add `heal` section to `.veridical.yaml.template` with documented options
- [ ] 2.4 Add unit tests for `HealConfig` validation

## 3. CLI Command
- [ ] 3.1 Create `src/veridical/cli/heal.py` with `veri heal` Typer command
- [ ] 3.2 Implement `--repo` and `--issue` options for single-issue mode
- [ ] 3.3 Implement `--watch` flag for continuous webhook/polling mode
- [ ] 3.4 Implement `--auto-spec` flag for auto-generating OpenSpec proposals
- [ ] 3.5 Implement `--dry-run` flag to show what would happen without executing
- [ ] 3.6 Register `heal` command in main CLI app

## 4. Integration with Supervisor
- [ ] 4.1 Wire intake pipeline output into `Supervisor.run()` task_description parameter
- [ ] 4.2 Wire intake pipeline output into `LocalSupervisor.run()` for local mode
- [ ] 4.3 On success, invoke `PRPublisher` to create PR with issue link and verification report
- [ ] 4.4 On failure, post a comment on the issue with diagnostic summary

## 5. Tests
- [ ] 5.1 Unit tests for `IssueFetcher` with mocked GitHub API responses
- [ ] 5.2 Unit tests for `TriageClassifier` with sample issue bodies
- [ ] 5.3 Unit tests for `TaskGenerator` output format
- [ ] 5.4 Unit tests for `PRPublisher` with mocked GitHub API
- [ ] 5.5 Integration test: full heal pipeline with mock worker (issue -> task -> verify -> PR)
- [ ] 5.6 Integration test: `veri heal --dry-run` output validation
