from __future__ import annotations

from datetime import datetime

import pytest
from typer.testing import CliRunner

from veridical.cli.main import app
from veridical.intake.models import GitHubIssue
from veridical.models.result import LoopResult

runner = CliRunner()


@pytest.mark.integration
class TestHealPipeline:
    def test_full_pipeline_mocked_success_opens_pr(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VERIDICAL_WORKER__BACKEND", "local")
        monkeypatch.setenv("VERIDICAL_HEAL__ENABLE_AUTO_PR", "true")
        monkeypatch.setenv("VERIDICAL_HEAL__GITHUB_TOKEN_ENV_VAR", "GITHUB_TOKEN")
        monkeypatch.setenv("GITHUB_TOKEN", "t")

        async def fake_fetch_issue(*_args: object, **_kwargs: object) -> GitHubIssue:
            return GitHubIssue(
                owner="o",
                repo="r",
                number=1,
                title="Bug",
                body="Details",
                url="https://github.com/o/r/issues/1",
                labels=["bug"],
                author="alice",
            )

        from veridical.intake.fetcher import IssueFetcher

        monkeypatch.setattr(IssueFetcher, "fetch_issue", fake_fetch_issue)

        async def fake_run(*_args: object, **_kwargs: object) -> LoopResult:
            return LoopResult(
                success=True,
                iterations=1,
                started_at=datetime.now(),
                completed_at=datetime.now(),
                final_commit="abc123",
                target_branch="feat/fix-bug",
            )

        from veridical.local.supervisor import LocalSupervisor

        monkeypatch.setattr(LocalSupervisor, "run", fake_run)

        published: dict[str, object] = {"called": False}

        async def fake_publish(*_args: object, **_kwargs: object) -> object:
            published["called"] = True

            class _PR:
                url = "https://github.com/o/r/pull/1"
                number = 1

            return _PR()

        from veridical.intake.publisher import PRPublisher

        monkeypatch.setattr(PRPublisher, "publish", fake_publish)

        result = runner.invoke(app, ["heal", "--repo", "o/r", "--issue", "1"])
        assert result.exit_code == 0
        assert published["called"] is True
        assert "Opened PR" in result.stdout
