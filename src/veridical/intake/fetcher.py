from __future__ import annotations

import os

import httpx

from veridical.exceptions import APIError, AuthenticationError, RateLimitError
from veridical.intake.models import GitHubIssue


class IssueFetcher:
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
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = self._get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def fetch_issue(self, *, owner: str, repo: str, number: int) -> GitHubIssue:
        url = f"{self._base_url}/repos/{owner}/{repo}/issues/{number}"
        async with httpx.AsyncClient(timeout=self._timeout, headers=self._headers()) as client:
            resp = await client.get(url)

        if resp.status_code == 401:
            raise AuthenticationError(details=resp.text)
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            retry_after = None
            if "Retry-After" in resp.headers:
                try:
                    retry_after = float(resp.headers["Retry-After"])
                except ValueError:
                    retry_after = None
            raise RateLimitError(retry_after=retry_after, details=resp.text)
        if resp.status_code >= 400:
            raise APIError(
                "GitHub API request failed",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        data = resp.json()
        labels = [lbl.get("name", "") for lbl in data.get("labels", []) if isinstance(lbl, dict)]
        issue = GitHubIssue(
            owner=owner,
            repo=repo,
            number=number,
            title=str(data.get("title", "")),
            body=str(data.get("body", "") or ""),
            url=str(data.get("html_url", "")),
            labels=[lbl for lbl in labels if lbl],
            author=(data.get("user") or {}).get("login"),
        )
        return issue

    async def post_comment(
        self,
        *,
        owner: str,
        repo: str,
        number: int,
        body: str,
    ) -> None:
        url = f"{self._base_url}/repos/{owner}/{repo}/issues/{number}/comments"
        async with httpx.AsyncClient(timeout=self._timeout, headers=self._headers()) as client:
            resp = await client.post(url, json={"body": body})

        if resp.status_code == 401:
            raise AuthenticationError(details=resp.text)
        if resp.status_code >= 400:
            raise APIError(
                "GitHub API request failed",
                status_code=resp.status_code,
                response_body=resp.text,
                details=str(dict(resp.headers)),
            )
