"""Learn command - analyze work log history and manage learned rules."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from veridical.config.loader import load_config
from veridical.learning.estimator import DifficultyEstimator
from veridical.learning.optimizer import PromptOptimizer
from veridical.learning.patterns import PatternAnalyzer
from veridical.learning.rules import RuleManager

console = Console()

learn_app = typer.Typer(
    name="learn",
    help="Analyze work log history and manage learned rules",
    no_args_is_help=True,
)


def _get_worklog_dir(config_path: Path | None) -> tuple[Path, object]:
    """Load config and return (worklog_dir, config)."""
    config = load_config(config_path)
    repo_path = Path.cwd()
    worklog_dir = repo_path / config.worklog.directory
    return worklog_dir, config


@learn_app.command("analyze")
def learn_analyze(
    config_path: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to configuration file"),
    ] = None,
) -> None:
    """Display pattern insights from work log history."""
    config = load_config(config_path)
    repo_path = Path.cwd()
    worklog_dir = repo_path / config.worklog.directory

    if not worklog_dir.exists():
        console.print(
            "[bold red]No work logs found.[/bold red] "
            "Run `veri run` or `veri local` first to generate work logs."
        )
        raise typer.Exit(code=1)

    analyzer = PatternAnalyzer(min_runs=config.learning.min_runs_for_analysis)
    report = analyzer.analyze(worklog_dir)

    if not report.sufficient_data:
        console.print(f"[yellow]{report.message}[/yellow]")
        raise typer.Exit(code=0)

    # Display report
    console.print(f"\n[bold]Pattern Analysis Report[/bold] ({report.total_runs_analyzed} runs)\n")

    # Gate failure frequencies
    if report.gate_failure_frequencies:
        table = Table(title="Gate Failure Frequencies")
        table.add_column("Gate", style="cyan")
        table.add_column("Failures", justify="right")
        table.add_column("Total", justify="right")
        table.add_column("Rate", justify="right")
        table.add_column("1st Iter Rate", justify="right")

        for freq in report.gate_failure_frequencies:
            rate_style = (
                "red"
                if freq.failure_rate >= 0.5
                else "yellow"
                if freq.failure_rate >= 0.3
                else "green"
            )
            table.add_row(
                freq.gate_name,
                str(freq.failure_count),
                str(freq.total_runs),
                f"[{rate_style}]{freq.failure_rate:.0%}[/{rate_style}]",
                f"{freq.first_iteration_failure_rate:.0%}",
            )
        console.print(table)
        console.print()

    # Stagnation patterns
    if report.stagnation_patterns:
        table = Table(title="Stagnation Patterns")
        table.add_column("Diff Hash", style="dim")
        table.add_column("Occurrences", justify="right")
        table.add_column("Affected Tasks")

        for pattern in report.stagnation_patterns:
            tasks = "; ".join(pattern.affected_task_descriptions[:3])
            table.add_row(pattern.diff_hash, str(pattern.occurrence_count), tasks)
        console.print(table)
        console.print()

    # Error categories
    if report.error_categories:
        table = Table(title="Error Categories")
        table.add_column("Category", style="cyan")
        table.add_column("Frequency", justify="right")
        table.add_column("Example")

        for cat in report.error_categories:
            example = cat.example_excerpts[0][:80] + "..." if cat.example_excerpts else ""
            table.add_row(cat.category, str(cat.frequency), example)
        console.print(table)
        console.print()

    console.print(f"[dim]Average iterations per run: {report.average_iterations_per_run}[/dim]")


@learn_app.command("apply")
def learn_apply(
    agents_md: Annotated[
        bool,
        typer.Option("--agents-md", help="Apply rules to AGENTS.md instead of rules file"),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to configuration file"),
    ] = None,
) -> None:
    """Apply learned rules from pattern analysis."""
    config = load_config(config_path)
    repo_path = Path.cwd()
    worklog_dir = repo_path / config.worklog.directory

    if not worklog_dir.exists():
        console.print(
            "[bold red]No work logs found.[/bold red] "
            "Run `veri run` or `veri local` first to generate work logs."
        )
        raise typer.Exit(code=1)

    # Analyze patterns
    analyzer = PatternAnalyzer(min_runs=config.learning.min_runs_for_analysis)
    report = analyzer.analyze(worklog_dir)

    if not report.sufficient_data:
        console.print(f"[yellow]{report.message}[/yellow]")
        raise typer.Exit(code=0)

    # Load existing rules
    rules_path = repo_path / config.learning.rules_file
    manager = RuleManager(rules_path)
    existing_rules = manager.load()

    # Generate new rules
    optimizer = PromptOptimizer()
    new_rules = optimizer.generate_rules(report, existing_rules)

    if not new_rules:
        console.print("[yellow]No new rules generated from current patterns.[/yellow]")
        raise typer.Exit(code=0)

    # Display proposed rules
    console.print(f"\n[bold]Proposed Rules ({len(new_rules)}):[/bold]\n")
    for rule in new_rules:
        console.print(f"  - {rule.rule_text} [dim](confidence: {rule.confidence_score:.0%})[/dim]")
    console.print()

    if agents_md:
        # Apply to AGENTS.md
        agents_path = repo_path / "AGENTS.md"

        # Show diff preview
        try:
            preview = manager.apply_to_agents_md(new_rules, agents_path, confirmed=False)
        except PermissionError as e:
            preview = str(e)

        console.print("[bold]Preview of changes to AGENTS.md:[/bold]")
        console.print(preview)

        confirmed = typer.confirm("Apply these rules to AGENTS.md?")
        if confirmed:
            manager.apply_to_agents_md(new_rules, agents_path, confirmed=True)
            console.print("[bold green]Rules applied to AGENTS.md.[/bold green]")
        else:
            console.print("[yellow]Cancelled.[/yellow]")
    else:
        # Save to rules file
        confirmed = typer.confirm("Save these rules?")
        if confirmed:
            # Merge with existing: update existing, add new
            existing_by_id = {r.id: r for r in existing_rules}
            for rule in new_rules:
                existing_by_id[rule.id] = rule
            all_rules = list(existing_by_id.values())

            manager.save(all_rules)
            console.print(f"[bold green]Saved {len(all_rules)} rules to {rules_path}.[/bold green]")
        else:
            console.print("[yellow]Cancelled.[/yellow]")


@learn_app.command("predict")
def learn_predict(
    task: Annotated[
        str,
        typer.Argument(help="Task description to predict difficulty for"),
    ],
    config_path: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to configuration file"),
    ] = None,
) -> None:
    """Estimate difficulty and iteration count for a given task."""
    config = load_config(config_path)
    repo_path = Path.cwd()
    worklog_dir = repo_path / config.worklog.directory

    if not worklog_dir.exists():
        console.print(
            "[bold red]No work logs found.[/bold red] "
            "Run `veri run` or `veri local` first to generate work logs."
        )
        raise typer.Exit(code=1)

    estimator = DifficultyEstimator(
        default_max_iterations=config.supervisor.max_iterations,
    )
    estimate = estimator.predict(task, worklog_dir)

    # Display estimate
    confidence_style = {
        "high": "green",
        "medium": "yellow",
        "low": "red",
    }
    style = confidence_style.get(estimate.confidence, "white")

    console.print("\n[bold]Difficulty Estimate[/bold]")
    console.print(f"  Predicted iterations: [bold]{estimate.predicted_iterations}[/bold]")
    console.print(f"  Confidence: [{style}]{estimate.confidence}[/{style}]")

    if estimate.similar_tasks:
        console.print("\n[bold]Similar Historical Tasks:[/bold]")
        table = Table()
        table.add_column("Task", max_width=60)
        table.add_column("Iterations", justify="right")
        table.add_column("Succeeded", justify="center")
        table.add_column("Similarity", justify="right")

        for st in estimate.similar_tasks:
            succeeded = "[green]Yes[/green]" if st.succeeded else "[red]No[/red]"
            table.add_row(
                st.task_description[:60],
                str(st.iterations_taken),
                succeeded,
                f"{st.similarity_score:.0%}",
            )
        console.print(table)
    else:
        console.print("\n[dim]No similar historical tasks found.[/dim]")


@learn_app.command("rules")
def learn_rules(
    prune: Annotated[
        bool,
        typer.Option("--prune", help="Remove stale rules (>90 days, <50% success rate)"),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to configuration file"),
    ] = None,
) -> None:
    """List, add, or remove learned rules."""
    config = load_config(config_path)
    repo_path = Path.cwd()
    rules_path = repo_path / config.learning.rules_file
    manager = RuleManager(rules_path)

    if prune:
        count = manager.prune(max_age_days=90)
        if count > 0:
            console.print(f"[bold green]Pruned {count} stale rule(s).[/bold green]")
        else:
            console.print("[dim]No stale rules to prune.[/dim]")
        return

    rules = manager.load()

    if not rules:
        console.print("[dim]No learned rules found.[/dim]")
        console.print("[dim]Run `veri learn apply` to generate rules from work log history.[/dim]")
        return

    table = Table(title=f"Learned Rules ({len(rules)})")
    table.add_column("ID", style="dim", max_width=10)
    table.add_column("Rule")
    table.add_column("Confidence", justify="right")
    table.add_column("Created", max_width=12)
    table.add_column("Applied", justify="right")
    table.add_column("Success Rate", justify="right")

    for rule in rules:
        conf_style = (
            "green"
            if rule.confidence_score >= 0.7
            else "yellow"
            if rule.confidence_score >= 0.4
            else "red"
        )
        table.add_row(
            rule.id,
            rule.rule_text,
            f"[{conf_style}]{rule.confidence_score:.0%}[/{conf_style}]",
            rule.created_at.strftime("%Y-%m-%d"),
            str(rule.applied_count),
            f"{rule.success_rate:.0%}",
        )

    console.print(table)
