from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

from veridical.exceptions import APIError, AuthenticationError
from veridical.synchronizer.git import GitWrapper

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class PublishedPR:
    url: str
    number: int


class PRPublisher:
    def __init__(
        self,
        *,
        token: str | None = None,
        base_url: str = "https://api.github.com",
        timeout: float = 30.0,
    ) -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _get_token(self) -> str | None:
        return self._token or os.environ.get("GITHUB_TOKEN")

    def _headers(self) -> dict[str, str]:
        token = self._get_token()
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _parse_remote(self, remote_url: str) -> tuple[str, str]:
        m = re.search(r"github.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)", remote_url)
        if not m:
            raise ValueError(f"Unsupported remote URL: {remote_url}")
        return m.group("owner"), m.group("repo")

    def _push_branch(self, repo_path: Path, branch: str) -> None:
        result = subprocess.run(
            ["git", "push", "-u", "origin", branch],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise APIError("Failed to push branch to origin", details=result.stderr.strip())

    async def publish(
        self,
        *,
        repo_path: Path,
        head_branch: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> PublishedPR:
        git = GitWrapper(repo_path)
        remote = git.get_remote_url("origin")
        owner, repo = self._parse_remote(remote)

        self._push_branch(repo_path, head_branch)

        url = f"{self._base_url}/repos/{owner}/{repo}/pulls"
        payload = {
            "title": title,
            "head": head_branch,
            "base": base_branch,
            "body": body,
        }
        async with httpx.AsyncClient(timeout=self._timeout, headers=self._headers()) as client:
            resp = await client.post(url, json=payload)

        if resp.status_code == 401:
            raise AuthenticationError(details=resp.text)
        if resp.status_code >= 400:
            raise APIError(
                "GitHub API request failed",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        data = resp.json()
        return PublishedPR(url=str(data.get("html_url", "")), number=int(data.get("number", 0)))
