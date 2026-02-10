"""Output formatters for run reports."""

from io import StringIO

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from veridical.report.models import RunSummary


class TerminalFormatter:
    """Renders a RunSummary as Rich tables for terminal display."""

    def format(self, summary: RunSummary, console: Console | None = None) -> str:
        """Render the summary to a string using Rich.

        Args:
            summary: The run summary to render
            console: Optional console; if None a string buffer is used

        Returns:
            Rendered string
        """
        buf = StringIO()
        con = console or Console(file=buf, force_terminal=True)

        # Header panel
        outcome_style = "bold green" if summary.outcome == "success" else "bold red"
        header_text = Text()
        header_text.append(f"Run: {summary.session_id}\n")
        header_text.append(f"Task: {summary.task_description}\n")
        header_text.append(f"Date: {summary.run_date}\n")
        header_text.append("Outcome: ")
        header_text.append(summary.outcome.upper(), style=outcome_style)
        con.print(Panel(header_text, title="Run Report"))

        # Aggregate metrics
        metrics = Table(title="Aggregate Metrics", show_header=False)
        metrics.add_column("Metric", style="cyan")
        metrics.add_column("Value")
        metrics.add_row("Total Iterations", str(summary.total_iterations))
        if summary.total_duration_seconds is not None:
            metrics.add_row("Total Duration", f"{summary.total_duration_seconds:.1f}s")
        if summary.most_failed_gate:
            metrics.add_row("Most Failed Gate", summary.most_failed_gate)
        if summary.cost.total_api_calls > 0:
            metrics.add_row("Total API Calls", str(summary.cost.total_api_calls))
        if summary.cost.total_estimated_tokens > 0:
            metrics.add_row("Estimated Tokens", str(summary.cost.total_estimated_tokens))
        if summary.cost.total_vm_time_seconds > 0:
            metrics.add_row("VM Time", f"{summary.cost.total_vm_time_seconds:.1f}s")
        con.print(metrics)

        # Per-iteration table
        iter_table = Table(title="Iteration Breakdown")
        iter_table.add_column("#", justify="right", style="dim")
        iter_table.add_column("Duration", justify="right")
        iter_table.add_column("Gates Failed")
        iter_table.add_column("Result")
        iter_table.add_column("Feedback Excerpt", max_width=60)

        for it in summary.iterations:
            dur = f"{it.duration_seconds:.1f}s" if it.duration_seconds else "-"
            failed = ", ".join(it.gates_failed) if it.gates_failed else "-"
            if it.verification_passed is True:
                result = "[green]PASS[/green]"
            elif it.verification_passed is False:
                result = "[red]FAIL[/red]"
            else:
                result = "[dim]-[/dim]"
            excerpt = it.feedback_excerpt or "-"
            if len(excerpt) > 57:
                excerpt = excerpt[:57] + "..."
            iter_table.add_row(str(it.iteration), dur, failed, result, excerpt)

        con.print(iter_table)

        # Pattern insights
        if summary.patterns:
            con.print()
            con.print("[bold]Pattern Insights[/bold]")
            for p in summary.patterns:
                icon = {
                    "frequent_failure": "[yellow]⚠[/yellow]",
                    "first_iter_failure": "[cyan]i[/cyan]",
                    "stagnation": "[red]⛔[/red]",
                }.get(p.category, "•")
                con.print(f"  {icon} {p.description}")

        if console is None:
            return buf.getvalue()
        return ""


class JsonFormatter:
    """Renders a RunSummary as JSON."""

    def format(self, summary: RunSummary) -> str:
        """Render the summary as a JSON string.

        Args:
            summary: The run summary to render

        Returns:
            JSON string
        """
        return summary.model_dump_json(indent=2)


class HtmlFormatter:
    """Renders a RunSummary as a single-file HTML report with embedded CSS."""

    def format(self, summary: RunSummary) -> str:
        """Render the summary as an HTML string.

        Args:
            summary: The run summary to render

        Returns:
            HTML string
        """
        outcome_class = "success" if summary.outcome == "success" else "failure"

        # Build iteration rows
        iter_rows = []
        for it in summary.iterations:
            dur = f"{it.duration_seconds:.1f}s" if it.duration_seconds else "-"
            failed = ", ".join(it.gates_failed) if it.gates_failed else "-"
            if it.verification_passed is True:
                result = '<span class="pass">PASS</span>'
            elif it.verification_passed is False:
                result = '<span class="fail">FAIL</span>'
            else:
                result = "-"
            excerpt = _html_escape(it.feedback_excerpt or "-")
            if len(excerpt) > 200:
                excerpt = excerpt[:200] + "..."
            iter_rows.append(
                f"<tr><td>{it.iteration}</td><td>{dur}</td>"
                f"<td>{_html_escape(failed)}</td><td>{result}</td>"
                f"<td class='excerpt'>{excerpt}</td></tr>"
            )

        # Build pattern items
        pattern_items = ""
        if summary.patterns:
            items = "".join(
                f"<li class='{p.category}'>{_html_escape(p.description)}</li>"
                for p in summary.patterns
            )
            pattern_items = f"<h2>Pattern Insights</h2><ul>{items}</ul>"

        # Cost section
        cost_section = ""
        if summary.cost.total_api_calls > 0 or summary.cost.total_estimated_tokens > 0:
            cost_section = f"""
            <h2>Cost Summary</h2>
            <table class="metrics">
                <tr><td>API Calls</td><td>{summary.cost.total_api_calls}</td></tr>
                <tr><td>Estimated Tokens</td><td>{summary.cost.total_estimated_tokens}</td></tr>
                <tr><td>VM Time</td><td>{summary.cost.total_vm_time_seconds:.1f}s</td></tr>
            </table>"""

        duration_str = (
            f"{summary.total_duration_seconds:.1f}s" if summary.total_duration_seconds else "-"
        )
        most_failed = summary.most_failed_gate or "-"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Veridical Run Report - {_html_escape(summary.session_id)}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         max-width: 960px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a;
         background: #fafafa; }}
  h1 {{ border-bottom: 2px solid #333; padding-bottom: 0.5rem; }}
  .outcome {{ display: inline-block; padding: 0.2rem 0.8rem; border-radius: 4px;
              font-weight: bold; text-transform: uppercase; }}
  .outcome.success {{ background: #d4edda; color: #155724; }}
  .outcome.failure {{ background: #f8d7da; color: #721c24; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #dee2e6; padding: 0.5rem; text-align: left; }}
  th {{ background: #e9ecef; }}
  .metrics td:first-child {{ font-weight: bold; width: 200px; }}
  .pass {{ color: #155724; font-weight: bold; }}
  .fail {{ color: #721c24; font-weight: bold; }}
  .excerpt {{ font-size: 0.85rem; color: #555; max-width: 400px;
              overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ padding: 0.3rem 0; }}
  li.frequent_failure::before {{ content: "⚠ "; }}
  li.first_iter_failure::before {{ content: "i "; }}
  li.stagnation::before {{ content: "⛔ "; }}
</style>
</head>
<body>
<h1>Veridical Run Report</h1>
<p><strong>Session:</strong> {_html_escape(summary.session_id)}</p>
<p><strong>Task:</strong> {_html_escape(summary.task_description)}</p>
<p><strong>Date:</strong> {summary.run_date}</p>
<p><strong>Outcome:</strong> <span class="outcome {outcome_class}">{summary.outcome}</span></p>

<h2>Aggregate Metrics</h2>
<table class="metrics">
  <tr><td>Total Iterations</td><td>{summary.total_iterations}</td></tr>
  <tr><td>Total Duration</td><td>{duration_str}</td></tr>
  <tr><td>Most Failed Gate</td><td>{_html_escape(most_failed)}</td></tr>
</table>

{cost_section}

<h2>Iteration Breakdown</h2>
<table>
  <thead><tr><th>#</th><th>Duration</th><th>Gates Failed</th><th>Result</th><th>Feedback</th></tr></thead>
  <tbody>{"".join(iter_rows)}</tbody>
</table>

{pattern_items}

<footer style="margin-top:2rem;color:#888;font-size:0.8rem;">
  Generated by Veridical at {summary.completed_at.isoformat()}
</footer>
</body>
</html>"""


def _html_escape(text: str) -> str:
    """Minimal HTML escaping."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def get_formatter(
    format_name: str,
) -> TerminalFormatter | JsonFormatter | HtmlFormatter:
    """Get a formatter by name.

    Args:
        format_name: One of 'terminal', 'json', 'html'

    Returns:
        Formatter instance

    Raises:
        ValueError: If format_name is not recognized
    """
    formatters = {
        "terminal": TerminalFormatter,
        "json": JsonFormatter,
        "html": HtmlFormatter,
    }
    cls = formatters.get(format_name)
    if cls is None:
        raise ValueError(f"Unknown format '{format_name}'. Supported: {', '.join(formatters)}")
    return cls()
