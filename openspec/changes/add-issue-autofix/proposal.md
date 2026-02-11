# Change: Add GitHub Issue Auto-Fix Pipeline (`veri heal`)

## Why
Veridical's core strength is its local verification loop, but today it requires a human to manually formulate tasks and invoke the CLI. To achieve true self-healing, Veridical needs an automated intake pipeline that accepts a GitHub issue (bug report, feature request) and autonomously produces a verified, PR-ready fix. No competitor in the supervisory-control space (SWE-agent, OpenHands, Factory.ai) combines issue intake with local truth verification — this is Veridical's differentiator.

## What Changes
- Add a new `veridical.intake` module with `IssueFetcher` (GitHub API), `Triage` classifier, and `TaskGenerator`
- Add a new CLI command `veri heal` that accepts `--repo`, `--issue`, and optional `--watch` for continuous mode
- Add `HealConfig` section to `.veridical.yaml` for GitHub token, triage settings, and auto-PR behavior
- Integrate intake pipeline with the existing `Supervisor.run()` and `LocalSupervisor.run()` loops
- Auto-generate OpenSpec proposals for complex issues (optional, gated by `--auto-spec` flag)
- On success, open a GitHub PR with issue link, root-cause summary, and verification evidence

## Impact
- Affected specs: `cli`, `config`, `supervisor`
- New capability: `intake` (new spec)
- Affected code: `src/veridical/intake/` (new), `src/veridical/cli/heal.py` (new), `src/veridical/config/schema.py`
