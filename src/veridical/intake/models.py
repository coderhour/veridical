from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GitHubIssue:
    owner: str
    repo: str
    number: int
    title: str
    body: str
    url: str
    labels: list[str]
    author: str | None
