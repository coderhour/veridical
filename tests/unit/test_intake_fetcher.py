from __future__ import annotations

import pytest
import respx
from httpx import Response

from veridical.exceptions import APIError, AuthenticationError
from veridical.intake.fetcher import IssueFetcher


@pytest.mark.unit
class TestIssueFetcher:
    @pytest.mark.asyncio
    async def test_fetch_issue_success(self) -> None:
        fetcher = IssueFetcher(token="t", base_url="https://api.github.com")

        with respx.mock:
            route = respx.get("https://api.github.com/repos/o/r/issues/1").mock(
                return_value=Response(
                    200,
                    json={
                        "title": "Bug",
                        "body": "Details",
                        "html_url": "https://github.com/o/r/issues/1",
                        "labels": [{"name": "bug"}],
                        "user": {"login": "alice"},
                    },
                )
            )
            issue = await fetcher.fetch_issue(owner="o", repo="r", number=1)

        assert route.called
        assert issue.number == 1
        assert issue.title == "Bug"
        assert issue.labels == ["bug"]
        assert issue.author == "alice"

    @pytest.mark.asyncio
    async def test_fetch_issue_unauthorized(self) -> None:
        fetcher = IssueFetcher(token="bad", base_url="https://api.github.com")

        with respx.mock:
            respx.get("https://api.github.com/repos/o/r/issues/1").mock(
                return_value=Response(401, text="nope")
            )
            with pytest.raises(AuthenticationError):
                await fetcher.fetch_issue(owner="o", repo="r", number=1)

    @pytest.mark.asyncio
    async def test_post_comment_error(self) -> None:
        fetcher = IssueFetcher(token="t", base_url="https://api.github.com")

        with respx.mock:
            respx.post("https://api.github.com/repos/o/r/issues/1/comments").mock(
                return_value=Response(500, text="boom")
            )
            with pytest.raises(APIError):
                await fetcher.post_comment(owner="o", repo="r", number=1, body="hi")
