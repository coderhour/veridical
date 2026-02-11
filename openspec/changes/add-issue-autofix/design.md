## Context
Veridical currently requires manual task formulation and CLI invocation. To enable self-healing, the system needs an automated intake pipeline that bridges GitHub issues to the existing supervisor loop. This is a cross-cutting change spanning a new module (`intake`), configuration, CLI, and supervisor integration.

## Goals / Non-Goals
- Goals:
  - Accept a GitHub issue and produce a verified fix with minimal human intervention
  - Reuse existing `Supervisor.run()` and `LocalSupervisor.run()` without modifying their core logic
  - Support both single-issue and continuous watch modes
  - Produce PR-ready output with traceability back to the issue
- Non-Goals:
  - Building a full GitHub App or OAuth flow (use personal access tokens initially)
  - Supporting non-GitHub issue trackers in v1 (Jira, Linear, etc.)
  - Replacing the existing `veri run` / `veri local` workflows

## Decisions
- **GitHub API via `httpx`**: Reuse the existing async HTTP pattern from the Jules API client. No new dependency needed since `httpx` is already in the dependency tree.
- **Triage uses local heuristics first**: Classify by label/title keywords before optionally using an LLM. Keeps the default path fast and free.
- **TaskGenerator produces a standard task string**: The output is a plain string compatible with `Supervisor.run(task_description=...)`, avoiding any interface changes to the supervisor.
- **PRPublisher uses GitHub REST API**: Creates a PR with a structured body containing issue link, verification summary, and iteration count.
- Alternatives considered:
  - GitHub webhooks for watch mode → Deferred; polling is simpler for v1, webhooks can be added later.
  - Full OpenSpec proposal generation per issue → Made optional via `--auto-spec` flag; many bug fixes don't need a spec.

## Risks / Trade-offs
- **GitHub API rate limits** → Mitigated by respecting `X-RateLimit-Remaining` headers and exponential backoff.
- **Triage accuracy** → Heuristic triage may misclassify; LLM fallback improves accuracy but adds latency/cost.
- **Security: GitHub token handling** → Token read from `GITHUB_TOKEN` env var only, never from config files. Same pattern as `JULES_API_KEY`.

## Open Questions
- Should `veri heal --watch` use GitHub webhooks (requires a server) or polling with configurable interval?
- Should failed heal attempts auto-label the issue (e.g., `veridical:failed`) for triage?
