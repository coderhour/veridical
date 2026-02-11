from __future__ import annotations

import pytest

from veridical.intake.models import GitHubIssue
from veridical.intake.task_generator import TaskGenerator
from veridical.intake.triage import TriageClassifier


@pytest.mark.unit
class TestTriageAndTaskGenerator:
    def test_triage_bug_label(self) -> None:
        issue = GitHubIssue(
            owner="o",
            repo="r",
            number=1,
            title="Something",
            body="",
            url="u",
            labels=["bug"],
            author=None,
        )
        triage = TriageClassifier().classify(issue)
        assert triage.category == "bug"

    def test_task_generator_contains_issue_link(self) -> None:
        issue = GitHubIssue(
            owner="o",
            repo="r",
            number=2,
            title="Crash",
            body="Steps to reproduce\n...",
            url="https://github.com/o/r/issues/2",
            labels=[],
            author="bob",
        )
        triage = TriageClassifier().classify(issue)
        task = TaskGenerator().generate(issue=issue, triage=triage)
        assert "Fix GitHub issue #2" in task
        assert "Issue: https://github.com/o/r/issues/2" in task
