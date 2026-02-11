from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from veridical.intake.models import GitHubIssue
    from veridical.intake.triage import TriageResult


class TaskGenerator:
    def generate(self, *, issue: GitHubIssue, triage: TriageResult) -> str:
        parts: list[str] = []
        parts.append(f"Fix GitHub issue #{issue.number}: {issue.title}")
        parts.append(f"Issue: {issue.url}")
        parts.append(f"Category: {triage.category}; Complexity: {triage.complexity}")
        parts.append("\nIssue description:\n" + (issue.body.strip() or "(no description)"))
        parts.append(
            "\nConstraints:\n"
            "- Make minimal, focused changes to address the issue\n"
            "- Add or update tests to cover the fix\n"
            "- Ensure the full test suite and linters pass\n"
        )
        return "\n".join(parts).strip() + "\n"
