from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import respx
from httpx import Response

from veridical.intake.publisher import PRPublisher
from veridical.synchronizer.git import GitWrapper


@pytest.mark.unit
class TestPRPublisher:
    @pytest.mark.asyncio
    async def test_publish_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        publisher = PRPublisher(token="t", base_url="https://api.github.com")

        def _fake_get_remote_url(self, remote: str = "origin") -> str:  # noqa: ARG001
            return "git@github.com:o/r.git"

        monkeypatch.setattr(GitWrapper, "get_remote_url", _fake_get_remote_url)

        def fake_run(*args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args=list(args), returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        with respx.mock:
            route = respx.post("https://api.github.com/repos/o/r/pulls").mock(
                return_value=Response(
                    201, json={"html_url": "https://github.com/o/r/pull/1", "number": 1}
                )
            )
            pr = await publisher.publish(
                repo_path=Path.cwd(),
                head_branch="feat/x",
                base_branch="main",
                title="t",
                body="b",
            )

        assert route.called
        assert pr.number == 1
        assert pr.url.endswith("/pull/1")
