## Context
The synchronizer applies patches from Jules without validation. This creates a security risk where a compromised or misbehaving agent could modify CI/CD pipelines, authentication code, or other sensitive files.

## Goals / Non-Goals
- **Goals**: Prevent unauthorized modifications to sensitive files, provide audit trail, enable configurable scope enforcement
- **Non-Goals**: Full static analysis of patch content, detecting malicious code patterns within allowed files

## Decisions
- **Decision**: Use glob pattern matching for file allowlist/denylist
  - Alternatives: regex (more powerful but harder to configure), explicit file lists (too rigid)
  - Rationale: Glob patterns are familiar, easy to configure, sufficient for path-based filtering

- **Decision**: Default to deny mode for known sensitive patterns
  - Alternatives: Default allow (less secure), require explicit config (bad UX)
  - Rationale: Security-first default with easy override via allowlist

## Risks / Trade-offs
- **False positives**: Legitimate changes to CI may be blocked → Mitigation: Clear error messages and easy override
- **Performance**: Pattern matching on every patch → Mitigation: Only parse diff once, patterns are simple

## Migration Plan
1. Add config with sensible defaults (existing users unaffected)
2. Default `strict_mode: false` initially (warnings only)
3. Document migration path to enable strict mode

## Open Questions
- Should we support per-proposal scope overrides in OpenSpec?
