"""Local supervisor implementation."""

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from veridical.local.gtr import GtrWorktreeManager
from veridical.local.runner import LocalRunner
from veridical.models.result import LoopResult
from veridical.supervisor.circuit_breaker import CircuitBreaker
from veridical.supervisor.state import SupervisorState
from veridical.verifier.quality_gate import Verifier
from veridical.worklog import WorkLogEntry, WorkLogWriter

if TYPE_CHECKING:
    from veridical.config.schema import VeridicalConfig
    from veridical.local.providers.protocol import LocalProvider

logger = logging.getLogger(__name__)


class LocalSupervisor:
    """Orchestrates the local verify-and-fix loop."""

    def __init__(
        self,
        config: "VeridicalConfig",
        repo_path: Path,
        *,
        verbose: bool = False,
        console: Console | None = None,
        provider: "LocalProvider | None" = None,
        gtr_branch: str | None = None,
    ) -> None:
        """Initialize the local supervisor.

        Args:
            config: Veridical configuration
            repo_path: Path to the repository root
            verbose: Enable verbose output
            console: Rich console instance
            provider: Optional local provider for command construction
            gtr_branch: Optional gtr worktree branch name. When set,
                a worktree is created before the loop and commands run inside it.
        """
        self.config = config
        self.repo_path = repo_path
        self.verbose = verbose
        self.console = console or Console()
        self.gtr_branch = gtr_branch
        self._gtr_manager: GtrWorktreeManager | None = None
        self._gtr_worktree_path: Path | None = None

        self._state = SupervisorState.IDLE
        self._circuit_breaker = CircuitBreaker(
            max_iterations=config.supervisor.max_iterations,
            max_consecutive_failures=config.supervisor.max_consecutive_failures,
            # Stagnation check might be less relevant without diffs, but we can keep it
            stagnation_threshold=config.supervisor.stagnation_threshold,
        )

        # Initialize components
        self.runner = LocalRunner(
            config.local, self.console, provider=provider, worktree_branch=gtr_branch
        )
        self.verifier = Verifier(config, repo_path)

        # Initialize work log writer if enabled
        self.worklog_writer: WorkLogWriter | None = None
        if config.worklog.enabled:
            self.worklog_writer = WorkLogWriter(
                project_path=repo_path,
                log_dir=config.worklog.directory,
            )

    async def run(
        self,
        task_description: str,
        tasks_file: Path | None = None,
    ) -> LoopResult:
        """Run the local supervisor loop.

        Args:
            task_description: Description of the task
            tasks_file: Optional path to the tasks.md file

        Returns:
            Result of the loop execution
        """
        # Set up gtr worktree if enabled
        if self.gtr_branch:
            self._gtr_manager = GtrWorktreeManager(self.repo_path)
            try:
                self._gtr_worktree_path = self._gtr_manager.create_worktree(self.gtr_branch)
                self.console.print(f"[dim]Created gtr worktree: {self._gtr_worktree_path}[/dim]")
                # Update verifier to run inside the worktree
                self.verifier = Verifier(self.config, self._gtr_worktree_path)
            except RuntimeError as e:
                self.console.print(f"[bold red]gtr worktree creation failed:[/bold red] {e}")
                return LoopResult.failure_result(
                    iterations=0,
                    started_at=datetime.now(),
                    failure_reason="gtr worktree creation failed",
                    error_context=str(e),
                )

        if tasks_file:
            self.verifier.current_tasks_file = tasks_file

        started_at = datetime.now()
        error_context: str | None = None

        self._circuit_breaker.reset()

        while not self._circuit_breaker.is_open:
            self._circuit_breaker.record_iteration()
            if self._circuit_breaker.is_open:
                break

            iteration = self._circuit_breaker.iteration_count
            self.console.print(f"\n[bold blue]Iteration {iteration}[/bold blue]")

            # Start work log entry
            log_entry = None
            if self.worklog_writer:
                log_entry = WorkLogEntry(
                    timestamp=datetime.now(),
                    iteration=iteration,
                    session_id="local",
                    task_description=task_description,
                    error_context=error_context,
                )

            # 1. Run Worker
            self._state = SupervisorState.RUNNING
            exit_code = await self.runner.run(error_context, task=task_description)

            if log_entry and self.runner.last_command:
                log_entry.prompt_sent = self.runner.last_command

            if exit_code != 0:
                self.console.print(
                    f"[yellow]Worker command failed with exit code {exit_code}[/yellow]"
                )
                # We record failure but might continue if it's just a test failure that verification will catch
                # However, usually if the build/run fails, verification will also fail.
                # Let's verify anyway to get structured feedback.

            # 2. Verify
            self._state = SupervisorState.VERIFYING
            verification_result = await self.verifier.run_all()

            if verification_result.passed:
                self._state = SupervisorState.SUCCESS
                self._circuit_breaker.record_success()

                if log_entry:
                    log_entry.verification_passed = True
                    log_entry.duration_seconds = (
                        datetime.now() - log_entry.timestamp
                    ).total_seconds()
                    self._write_log(log_entry)

                self.console.print("[bold green]Verification passed! Task completed.[/bold green]")

                # gtr: merge and optionally clean up
                self._gtr_merge_and_cleanup()

                return LoopResult(
                    success=True,
                    iterations=iteration,
                    started_at=started_at,
                    completed_at=datetime.now(),
                    final_commit=None,
                    target_branch=None,
                )

            # 3. Handle Failure
            self._state = SupervisorState.FAILED  # Transient failure
            self._circuit_breaker.record_failure()

            error_context = await self.verifier.generate_feedback(verification_result)

            if log_entry:
                log_entry.verification_passed = False
                log_entry.verification_errors = error_context
                log_entry.duration_seconds = (datetime.now() - log_entry.timestamp).total_seconds()
                self._write_log(log_entry)

            self.console.print("[bold red]Verification failed.[/bold red]")
            if self.verbose:
                self.console.print(f"[dim]{error_context}[/dim]")

        # Loop terminated
        self._state = SupervisorState.FAILED

        # If we tripped due to max iterations, report the max, not max + 1
        iterations = self._circuit_breaker.iteration_count
        if self._circuit_breaker.open_reason == "Maximum iterations exceeded":
            iterations -= 1

        # On failure, keep worktree intact for inspection
        self._gtr_report_preserved()

        return LoopResult.failure_result(
            iterations=iterations,
            started_at=started_at,
            failure_reason=self._circuit_breaker.open_reason or "Max iterations reached",
            error_context=error_context,
        )

    # ------------------------------------------------------------------
    # gtr helpers
    # ------------------------------------------------------------------

    def _gtr_merge_and_cleanup(self) -> None:
        """Merge the gtr worktree branch back and optionally clean up."""
        if not self.gtr_branch or not self._gtr_manager:
            return

        # Determine the branch to merge into (the branch the user was on)
        starting_branch = self._get_starting_branch()

        merged = self._gtr_manager.merge_worktree_branch(self.gtr_branch, starting_branch)
        if merged:
            self.console.print(
                f"[bold green]Merged {self.gtr_branch} into {starting_branch}[/bold green]"
            )
            if self.config.local.gtr_auto_cleanup:
                try:
                    self._gtr_manager.remove_worktree(self.gtr_branch)
                    self.console.print("[dim]Worktree cleaned up.[/dim]")
                except RuntimeError as e:
                    logger.warning(f"Failed to clean up worktree: {e}")
                    self.console.print(f"[yellow]Warning: worktree cleanup failed: {e}[/yellow]")
            else:
                self.console.print(
                    f"[dim]Worktree preserved (gtr_auto_cleanup=false): "
                    f"{self._gtr_worktree_path}[/dim]"
                )
        else:
            self.console.print(
                f"[yellow]Merge conflict: could not auto-merge {self.gtr_branch} "
                f"into {starting_branch}.[/yellow]"
            )
            self.console.print(
                f"[yellow]Your work is safe on branch {self.gtr_branch}.[/yellow]\n"
                f"[yellow]Worktree path: {self._gtr_worktree_path}[/yellow]\n"
                f"[yellow]To merge manually:[/yellow]\n"
                f"  git checkout {starting_branch}\n"
                f"  git merge {self.gtr_branch}"
            )

    def _gtr_report_preserved(self) -> None:
        """Report that the gtr worktree is preserved for inspection."""
        if not self.gtr_branch or not self._gtr_worktree_path:
            return
        self.console.print(
            f"[dim]Worktree preserved for inspection: {self._gtr_worktree_path} "
            f"(branch: {self.gtr_branch})[/dim]"
        )

    def _get_starting_branch(self) -> str:
        """Detect the current branch in the main repo."""
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        branch = result.stdout.strip()
        if not branch or branch == "HEAD":
            return self.config.git.base_branch
        return branch

    def _write_log(self, entry: WorkLogEntry) -> None:
        """Write entry to work log."""
        if self.worklog_writer:
            try:
                self.worklog_writer.write(entry)
            except Exception as e:
                logger.warning(f"Failed to write work log: {e}")
