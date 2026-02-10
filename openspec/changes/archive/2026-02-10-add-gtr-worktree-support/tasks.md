## 1. gtr Detection and Branch Name Generation
- [x] 1.1 Add `detect_gtr() -> bool` utility function that checks if `git gtr` is available on PATH (e.g., `shutil.which("git-gtr")` or running `git gtr list` and checking exit code)
- [x] 1.2 Add `generate_gtr_branch_name(spec_name: str | None, task_description: str) -> str` that produces a `veri/<sanitized-name>` branch name, reusing existing branch name sanitization logic
- [x] 1.3 Add unit tests for `detect_gtr()` and `generate_gtr_branch_name()`

## 2. Configuration
- [x] 2.1 Add `gtr_enabled: bool` field to `LocalConfig` in `config/schema.py` (default: `False`)
- [x] 2.2 Add `gtr_auto_cleanup: bool` field to `LocalConfig` (default: `True`)
- [x] 2.3 Update `.veridical.yaml.template` with `local.gtr_enabled` and `local.gtr_auto_cleanup` examples
- [x] 2.4 Add unit tests for new config fields

## 3. gtr Worktree Manager
- [x] 3.1 Create `src/veridical/local/gtr.py` module with `GtrWorktreeManager` class
- [x] 3.2 Implement `create_worktree(branch_name: str) -> Path` that runs `git gtr new <branch> --no-hooks --yes` and returns the worktree path
- [x] 3.3 Implement `remove_worktree(branch_name: str) -> None` that runs `git gtr rm <branch> --yes`
- [x] 3.4 Implement `get_worktree_path(branch_name: str) -> Path` that runs `git gtr go <branch>` and returns the path
- [x] 3.5 Add unit tests for `GtrWorktreeManager` (mocking subprocess calls)

## 4. LocalRunner Integration
- [x] 4.1 Extend `LocalRunner` to accept an optional `worktree_branch: str | None` parameter
- [x] 4.2 When `worktree_branch` is set, wrap the worker command with `git gtr run <branch>` prefix
- [x] 4.3 Add unit tests for `LocalRunner` with gtr-wrapped commands

## 5. LocalSupervisor Integration
- [x] 5.1 Update `LocalSupervisor` to accept gtr config and create worktree before the loop starts
- [x] 5.2 Pass worktree branch to `LocalRunner` when gtr is enabled
- [x] 5.3 Update verifier to use worktree path when gtr is enabled
- [x] 5.4 Add merge logic: on success, attempt to merge worktree branch back to starting branch
- [x] 5.5 Handle merge conflict: if merge fails, abort merge, keep worktree, display path and manual merge instructions
- [x] 5.6 Add cleanup logic: remove worktree after successful merge (when `gtr_auto_cleanup` is true), keep worktree on failure or merge conflict
- [x] 5.7 Add unit tests for `LocalSupervisor` with gtr enabled/disabled

## 6. CLI Integration
- [x] 6.1 Add `--gtr` flag to `veri local` command (opt-in, default off)
- [x] 6.2 Resolve gtr enablement: CLI `--gtr` flag OR `local.gtr_enabled` config
- [x] 6.3 When gtr is enabled, detect gtr availability and display error with install instructions if not found
- [x] 6.4 Auto-generate branch name from spec name or task description and display it to the user
- [x] 6.5 Add unit tests for CLI gtr flag handling

## 7. Integration Testing
- [x] 7.1 Add integration test: `veri local --gtr "Fix bug" --dry-run` validates gtr detection and branch name generation
- [x] 7.2 Add integration test: `veri local --gtr --provider claude-code --dry-run` combines provider and gtr options

## 8. Documentation
- [x] 8.1 Update README with gtr integration section and usage examples
- [x] 8.2 Update `.veridical.yaml.template` with gtr configuration examples
