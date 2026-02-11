from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from veridical.intake.models import GitHubIssue


@dataclass(frozen=True)
class TriageResult:
    category: str
    complexity: str
    reasons: list[str]


class TriageClassifier:
    def classify(self, issue: GitHubIssue) -> TriageResult:
        title = issue.title.lower()
        body = issue.body.lower()
        labels = [lbl.lower() for lbl in issue.labels]

        reasons: list[str] = []

        category = "question"
        if any(lbl in labels for lbl in ["bug", "type: bug", "kind/bug"]):
            category = "bug"
            reasons.append("bug label")
        elif any(lbl in labels for lbl in ["feature", "enhancement", "type: feature"]):
            category = "feature"
            reasons.append("feature label")
        elif any(k in title for k in ["bug", "error", "crash", "fail", "exception"]):
            category = "bug"
            reasons.append("bug keywords in title")
        elif any(k in title for k in ["feature", "enhancement", "support", "add "]):
            category = "feature"
            reasons.append("feature keywords in title")

        complexity = "small"
        if any(lbl in labels for lbl in ["complex", "large", "epic"]):
            complexity = "large"
            reasons.append("complexity label")
        elif len(body.splitlines()) > 50 or len(body) > 4000:
            complexity = "medium"
            reasons.append("long description")
        elif any(k in body for k in ["steps to reproduce", "stack trace", "traceback"]):
            complexity = "medium"
            reasons.append("debug details present")

        if not reasons:
            reasons.append("default heuristics")

        return TriageResult(category=category, complexity=complexity, reasons=reasons)
