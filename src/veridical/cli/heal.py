"""Heal command - intake a GitHub issue and attempt an automated verified fix."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from veridical.api.client import JulesClient
from veridical.config.loader import load_config
from veridical.exceptions import VeridicalError
from veridical.intake import IssueFetcher, PRPublisher, TaskGenerator, TriageClassifier
from veridical.models.result import LoopResult

console = Console()


def _parse_repo(repo: str) -> tuple[str, str]:
    if "/" not in repo:
        raise ValueError("--repo must be in the form 'owner/repo'")
    owner, name = repo.split("/", 1)
    owner = owner.strip()
    name = name.strip()
    if not owner or not name:
        raise ValueError("--repo must be in the form 'owner/repo'")
    return owner, name


def _render_result(result: LoopResult) -> None:
    style = "green" if result.success else "red"
    title = "SUCCESS" if result.success else "FAILED"

    content = f"""
[bold]Iterations:[/bold] {result.iterations}
[bold]Duration:[/bold] {result.duration_seconds:.2f}s
[bold]Started:[/bold] {result.started_at.isoformat()}
[bold]Completed:[/bold] {result.completed_at.isoformat()}
"""

    if result.final_commit:
        content += f"[bold]Final Commit:[/bold] {result.final_commit}\n"

    if result.target_branch:
        content += f"[bold]Target Branch:[/bold] {result.target_branch}\n"

    if result.failure_reason:
        content += f"\n[bold]Failure Reason:[/bold] {result.failure_reason}"

    if result.error_context:
        content += f"\n[bold]Error Context:[/bold]\n{result.error_context}"

    console.print(Panel(content, title=f"[{style}]{title}[/{style}]", border_style=style))


def _scaffold_openspec_change(*, repo: str, issue: int, title: str, url: str) -> Path:
    owner, name = _parse_repo(repo)
    change_id = f"heal-issue-{owner}-{name}-{issue}".lower().replace("_", "-")
    change_path = Path("openspec/changes") / change_id

    change_path.mkdir(parents=True, exist_ok=True)
    proposal = change_path / "proposal.md"
    tasks = change_path / "tasks.md"

    if not proposal.exists():
        proposal.write_text(
            "\n".join(
                [
                    f"# Change: Heal GitHub issue #{issue}",
                    "",
                    "## Why",
                    f"Auto-generated from {url}",
                    "",
                    "## What Changes",
                    f"- Implement fix for: {title}",
                    "- Add tests to prevent regression",
                    "",
                    "## Impact",
                    "- Affected specs: (unknown)",
                    "- Affected code: (unknown)",
                    "",
                ]
            )
        )

    if not tasks.exists():
        tasks.write_text(
            "\n".join(
                [
                    "## 1. Implementation",
                    "- [ ] 1.1 Reproduce issue locally",
                    "- [ ] 1.2 Implement fix",
                    "- [ ] 1.3 Add/adjust tests",
                    "- [ ] 1.4 Run full verification",
                    "",
                ]
            )
        )

    return tasks


async def _heal_once(
    *,
    repo: str,
    issue: int,
    config_path: Path | None,
    dry_run: bool,
    auto_spec: bool,
    verbose: bool,
) -> LoopResult:
    config = load_config(config_path)

    owner, name = _parse_repo(repo)

    fetcher = IssueFetcher(token=os.environ.get(config.heal.github_token_env_var))
    triage = TriageClassifier()
    generator = TaskGenerator()

    gh_issue = await fetcher.fetch_issue(owner=owner, repo=name, number=issue)
    triage_result = triage.classify(gh_issue)

    tasks_file: Path | None = None
    if auto_spec and triage_result.complexity in {"medium", "large"}:
        tasks_file = _scaffold_openspec_change(
            repo=repo,
            issue=issue,
            title=gh_issue.title,
            url=gh_issue.url,
        )
        console.print(f"[dim]Auto-generated OpenSpec tasks: {tasks_file}[/dim]")

    task_description = generator.generate(issue=gh_issue, triage=triage_result)

    if dry_run:
        console.print("[yellow]Dry run: would heal the following issue:[/yellow]")
        console.print(f"[dim]{gh_issue.url}[/dim]")
        console.print("\n[bold]Generated task description:[/bold]\n")
        console.print(task_description)
        return LoopResult.failure_result(
            iterations=0,
            started_at=datetime.now(),
            failure_reason="dry-run",
        )

    if config.worker.backend == "local":
        from veridical.local.supervisor import LocalSupervisor

        supervisor = LocalSupervisor(config, Path.cwd(), verbose=verbose, console=console)
        result = await supervisor.run(task_description, tasks_file=tasks_file)
    else:
        api_key = os.environ.get("JULES_API_KEY")
        if not api_key:
            console.print("[bold red]Error:[/bold red] JULES_API_KEY environment variable not set.")
            raise typer.Exit(code=1)

        async with JulesClient(
            api_key=api_key,
            base_url=config.jules.api_base_url,
            timeout=config.jules.poll_timeout,
        ) as client:
            from veridical.supervisor.loop import Supervisor
            from veridical.worker.jules import JulesWorker

            worker = JulesWorker(config, client, Path.cwd(), verbose=verbose, console=console)
            supervisor = Supervisor(config, worker, Path.cwd(), verbose=verbose, console=console)

            result = await supervisor.run(task_description, tasks_file=tasks_file)

    if result.success and config.heal.enable_auto_pr and result.target_branch:
        publisher = PRPublisher(token=os.environ.get(config.heal.github_token_env_var))
        pr_body = (
            f"Fixes {gh_issue.url}\n\n"
            f"Verification:\n- iterations: {result.iterations}\n- final_commit: {result.final_commit or ''}\n"
        ).strip()
        published = await publisher.publish(
            repo_path=Path.cwd(),
            head_branch=result.target_branch,
            base_branch=config.heal.pr_base_branch,
            title=f"Fix: {gh_issue.title} (#{gh_issue.number})",
            body=pr_body,
        )
        console.print(f"[bold green]Opened PR:[/bold green] {published.url}")

    if (not result.success) and config.heal.comment_on_failure:
        summary = result.failure_reason or "heal failed"
        if result.error_context:
            summary += "\n\n" + result.error_context[:1500]
        await fetcher.post_comment(owner=owner, repo=name, number=issue, body=summary)

    return result


def heal(
    repo: Annotated[
        str,
        typer.Option(
            "--repo",
            help="GitHub repository in the form owner/repo",
        ),
    ],
    issue: Annotated[
        int,
        typer.Option(
            "--issue",
            help="GitHub issue number",
            min=1,
        ),
    ],
    watch: Annotated[
        bool,
        typer.Option(
            "--watch",
            help="Continuously retry healing (polling) until success or interrupted",
        ),
    ] = False,
    auto_spec: Annotated[
        bool,
        typer.Option(
            "--auto-spec",
            help="Optionally generate an OpenSpec proposal for complex issues (best-effort)",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show what would happen without executing",
        ),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to configuration file",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output",
        ),
    ] = False,
) -> None:
    """Heal a GitHub issue by generating a task and running the supervisor loop."""

    try:
        config = load_config(config_path)

        async def _run_watch() -> None:
            while True:
                result = await _heal_once(
                    repo=repo,
                    issue=issue,
                    config_path=config_path,
                    dry_run=dry_run,
                    auto_spec=auto_spec,
                    verbose=verbose,
                )

                if dry_run:
                    return

                _render_result(result)

                if result.success:
                    return

                if not watch:
                    raise typer.Exit(code=1)

                console.print(
                    f"[dim]Waiting {config.heal.watch_interval_seconds}s before retry...[/dim]"
                )
                await asyncio.sleep(config.heal.watch_interval_seconds)

        asyncio.run(_run_watch())

    except VeridicalError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if e.details:
            console.print(f"[dim]{e.details}[/dim]")
        raise typer.Exit(code=1) from e
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e
