# Proposal: Remember Starting Branch

## Status

DRAFT

## Why

The current implementation assumes users are always on `main` branch when running `veri run` and merges directly to `base_branch`. This causes issues when users work on feature branches or when `main` is protected. By auto-creating a dedicated work branch, Veridical can safely isolate all changes and support diverse team workflows including PR-based processes.

## Problem Statement

The current branch strategy assumes the user is always on the `main` (or configured `base_branch`) when running `veri run`. This assumption is often incorrect because:

1. **Users work on feature branches**: Developers frequently work on feature branches (`feature/abc`, `fix/xyz`) rather than `main`.
2. **Protected main branches**: Many organizations have protected `main` branches that prevent direct pushes/merges without pull requests.
3. **Different team workflows**: Various teams use different branching strategies (GitFlow, trunk-based, etc.) where merging directly to `main` is inappropriate.

When Veridical completes successfully, it merges results to the configured `base_branch` (defaulting to `main`), which may not be safe or permitted.

## Proposed Solution

**Introduce `auto_create_work_branch` option (default: `true`)** that creates a dedicated work branch for all Veridical changes.

Key changes:

1. **New configuration option**: `git.auto_create_work_branch` (bool, default `true`)
2. **Auto-create work branch**: When enabled, create a branch based on `base_branch` with naming pattern:
   - `feat/<spec-name>` for feature work
   - `fix/<task-name>` for fixes
   - Branch names sanitized to alphanumeric + hyphens only
3. **All changes go to work branch**: Merge iteration branches to the work branch instead of `base_branch`
4. **Remember starting branch**: Still capture the original branch so user returns to it after completion
5. **CLI override**: `--target-branch` can override the auto-generated branch name

### Branch Naming

Branch names are sanitized:
- Convert to lowercase
- Replace spaces/underscores with hyphens
- Remove non-alphanumeric characters (except hyphens)
- Examples:
  - Spec "Add User Authentication" → `feat/add-user-authentication`
  - Task "Fix login bug" → `fix/fix-login-bug`

## User Impact

- **Safe by default**: Changes go to a feature branch, never directly to `main`
- **PR-friendly**: Users can push the work branch and create a PR
- **Minimal friction**: No extra configuration needed for most workflows
- **Flexible override**: Can disable via `auto_create_work_branch: false` or specify branch via `--target-branch`

## Scope

This change affects:
- `veridical.config.schema`: Add `auto_create_work_branch` to `GitConfig`
- `veridical.synchronizer.branch`: Branch detection, work branch creation, and sanitization logic
- `veridical.synchronizer.patch`: Create/use work branch as merge target
- `veridical.supervisor.loop`: Pass spec/task name for branch naming
- `veridical.cli.run`: Add `--target-branch` option

This change does **not** affect:
- How iteration branches are named (still uses prefix + iteration number)
- How patches are applied (still creates iteration branches)
- Existing `base_branch` configuration (used as source for work branch)

## Alternatives Considered

1. **Merge directly to starting branch**: Risky if user is on a shared branch; doesn't support protected branches.
2. **Require manual branch creation**: Adds friction to the autonomous workflow.
3. **Always create work branch with UUID**: Less readable than spec/task-based naming.

## Success Criteria

- `auto_create_work_branch: true` (default) creates `feat/<spec-name>` branch
- Running `veri run` from `main` creates work branch, merges there, user ends on `main`
- Branch names only contain `[a-z0-9-]` characters
- `--target-branch custom` overrides the auto-generated name
- `auto_create_work_branch: false` uses legacy behavior (merge to `base_branch`)
