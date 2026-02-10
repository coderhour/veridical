## Context
Veridical's `veri local` runs a verify-and-fix loop in the current working directory. When a user wants to work on multiple specs or bugs in parallel, they cannot run multiple `veri local` sessions because they all share the same git state. [gtr](https://github.com/coderabbitai/git-worktree-runner) is a lightweight bash CLI that wraps `git worktree` with quality-of-life features — creating isolated worktree directories per branch and running commands inside them.

## Goals / Non-Goals
- **Goals:**
  - Allow parallel `veri local` sessions via git worktrees
  - Auto-generate branch names from spec names or task descriptions
  - Minimal integration surface — delegate worktree management to `gtr`
  - Opt-in only; zero impact when disabled
- **Non-Goals:**
  - Bundling or installing gtr — users must install it separately
  - Replacing the existing synchronizer's branch management for `veri run` (Jules mode)
  - Supporting worktrees for the remote Jules workflow

## Decisions
- **Delegate to gtr CLI**: Rather than implementing git worktree operations in Python, shell out to `git gtr new` / `git gtr run` / `git gtr rm`. This keeps the integration thin and benefits from gtr's cross-platform support and configuration system.
  - *Alternative*: Use `git worktree` directly. Rejected because gtr handles file copying, hooks, and cleanup automatically.
- **Branch name generation**: Reuse the existing `sanitize_branch_name()` helper from `veridical.synchronizer.branch_utils` (or equivalent). Prefix with `veri/` to namespace worktree branches (e.g., `veri/add-user-auth`).
  - *Alternative*: Use `feat/` prefix like the synchronizer. Rejected to avoid confusion with human-created feature branches.
- **Execution model**: When gtr is enabled, `LocalRunner` wraps the worker command with `git gtr run <branch>` so the command executes inside the worktree directory. The runner itself stays in the original repo.
- **Merge-then-cleanup policy**: On success, the system attempts to merge the worktree branch back to the starting branch (the branch the user was on when they ran `veri local`). If the merge succeeds, the worktree is removed when `gtr_auto_cleanup` is enabled. If the merge fails (conflicts), the merge is aborted, the worktree is kept intact, and the user is instructed to merge manually. On loop failure, no merge is attempted and the worktree is preserved. This ensures completed work is never lost by cleanup.

## Risks / Trade-offs
- **External dependency**: gtr must be installed separately. Mitigation: detect at startup, provide clear error message with install instructions.
- **Worktree overhead**: Each worktree is a full checkout. Mitigation: gtr handles this efficiently; worktrees share the `.git` object store.
- **Verifier path**: The verifier currently runs in `repo_path`. When gtr is enabled, the verifier must run inside the worktree path. This requires passing the worktree path to the verifier.

## Open Questions
- None currently. The merge-then-cleanup policy ensures work is never lost: merge to starting branch on success, then optionally remove the worktree. On failure, the worktree is always preserved.
