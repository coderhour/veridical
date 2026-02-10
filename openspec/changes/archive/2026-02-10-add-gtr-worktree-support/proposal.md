# Change: Add gtr (Git Worktree Runner) support for parallel local development

## Why
When running `veri local` on multiple features or specs simultaneously, each run operates in the same working directory, making parallel execution impossible. By integrating [gtr](https://github.com/coderabbitai/git-worktree-runner), Veridical can spin up isolated git worktrees per task — each on its own auto-generated branch — so users can run multiple `veri local` sessions in parallel without conflicts.

## What Changes
- Add `--gtr` flag to `veri local` command (opt-in, disabled by default)
- Add `local.gtr_enabled` config field (default: `false`)
- When gtr is enabled, auto-generate a branch name from the spec name or task description (reusing existing `sanitize_branch_name` logic from the synchronizer)
- Before launching the worker, run `git gtr new <branch> --no-hooks` to create an isolated worktree, then execute the worker inside that worktree via `git gtr run <branch> <command>`
- On success, merge the worktree branch back to the starting branch, then optionally clean up the worktree with `git gtr rm <branch>`
- On failure, keep the worktree intact so the user can inspect or continue the work
- Add `gtr` detection: check if `git gtr` is available on PATH before attempting worktree operations
- Add `local.gtr_auto_cleanup` config field (default: `true`) to control whether worktrees are removed after completion

## Impact
- Affected specs: `cli`, `config`
- Affected code: `src/veridical/cli/local.py`, `src/veridical/config/schema.py`, `src/veridical/local/supervisor.py`, `src/veridical/local/runner.py`
- No breaking changes — gtr is opt-in and all existing behavior is preserved when disabled
