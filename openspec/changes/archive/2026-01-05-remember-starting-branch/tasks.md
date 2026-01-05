# Tasks: Remember Starting Branch

## Implementation Tasks

- [x] **Add `auto_create_work_branch` config option**: Add `auto_create_work_branch: bool = True` to `GitConfig` in `src/veridical/config/schema.py`.

- [x] **Add `get_current_branch()` to `GitWrapper`**: Implement a method in `src/veridical/synchronizer/git.py` that returns the current branch name, handling detached HEAD state gracefully.

- [x] **Add `sanitize_branch_name()` utility**: Create a helper function in `src/veridical/synchronizer/branch.py` that converts a string to a valid branch name (lowercase, alphanumeric + hyphens only).

- [x] **Update `BranchManager` to track starting branch**: Modify `src/veridical/synchronizer/branch.py` to capture and store the current branch on initialization.

- [x] **Add `create_work_branch()` method**: Implement method in `BranchManager` that creates a work branch (`feat/<name>` or `fix/<name>`) from `base_branch`, returning the new branch name.

- [x] **Update `Synchronizer` to manage work branch**: Modify `src/veridical/synchronizer/patch.py` to:
  - Track and expose the starting branch
  - Create work branch when `auto_create_work_branch` is enabled
  - Merge iteration branches to work branch instead of `base_branch`

- [x] **Add `--target-branch` CLI option**: Add an optional `--target-branch` / `-b` flag to the `veri run` command in `src/veridical/cli/run.py` that overrides the auto-generated work branch name.

- [x] **Update `Supervisor.run()` to pass task/spec name**: Modify `src/veridical/supervisor/loop.py` to pass the task description (for branch naming) and target branch override to the synchronizer.

- [x] **Add unit tests for branch sanitization**: Create tests in `tests/unit/test_branch_sanitization.py` covering:
  - Lowercase conversion
  - Space/underscore to hyphen
  - Special character removal
  - Edge cases (empty, numeric-only, etc.)

- [x] **Add unit tests for work branch creation**: Create tests in `tests/unit/test_work_branch.py` covering:
  - Work branch creation from base_branch
  - Starting branch capture
  - Override via `--target-branch`

- [x] **Add integration tests for work branch flow**: Add integration tests in `tests/integration/test_work_branch.py` verifying:
  - Full flow with auto_create_work_branch enabled
  - User returns to starting branch after completion
  - Work branch contains merged changes

- [x] **Update config templates**: Add `auto_create_work_branch: true` to all language templates in `src/veridical/config/defaults.py`.

- [x] **Update project documentation**: Update `README.md` to document the new `auto_create_work_branch` behavior and `--target-branch` option.
