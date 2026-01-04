from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from veridical.api.models import SourceContext
from veridical.dispatcher.session import Dispatcher


@pytest.mark.unit
class TestSourceContext:
    def test_from_remote_url_https(self) -> None:
        url = "https://github.com/owner/repo.git"
        ctx = SourceContext.from_remote_url(url)
        assert ctx.source == "sources/github/owner/repo"

    def test_from_remote_url_https_no_git(self) -> None:
        url = "https://github.com/owner/repo"
        ctx = SourceContext.from_remote_url(url)
        assert ctx.source == "sources/github/owner/repo"

    def test_from_remote_url_ssh(self) -> None:
        url = "git@github.com:owner/repo.git"
        ctx = SourceContext.from_remote_url(url)
        assert ctx.source == "sources/github/owner/repo"

    def test_from_remote_url_ssh_no_git(self) -> None:
        url = "git@github.com:owner/repo"
        ctx = SourceContext.from_remote_url(url)
        assert ctx.source == "sources/github/owner/repo"

    def test_invalid_url_not_github(self) -> None:
        with pytest.raises(ValueError, match="Only GitHub repos are supported"):
            SourceContext.from_remote_url("https://gitlab.com/owner/repo.git")

    def test_invalid_url_format(self) -> None:
        with pytest.raises(ValueError, match="Unsupported URL format"):
            SourceContext.from_remote_url("ftp://github.com/owner/repo")


@pytest.mark.unit
class TestDispatcherAutoDetect:
    @pytest.mark.asyncio
    async def test_auto_detect_source(self) -> None:
        with patch("veridical.dispatcher.session.GitWrapper") as MockGitWrapper:
            # Mock GitWrapper instance
            mock_git = MagicMock()
            mock_git.get_remote_url.return_value = "git@github.com:owner/repo.git"
            MockGitWrapper.return_value = mock_git

            # Mock dependencies
            config = MagicMock()
            config.git.base_branch = "main"
            config.jules.auto_approve_plans = True

            client = MagicMock()
            client.create_session = AsyncMock(return_value=MagicMock())

            # Initialize Dispatcher
            dispatcher = Dispatcher(config, client, repo_path=Path("/tmp"))

            # Call create_session without source
            await dispatcher.create_session("test prompt")

            # Verify GitWrapper usage
            mock_git.get_remote_url.assert_called_once()

            # Verify API call
            call_args = client.create_session.call_args[0][0]
            assert call_args.source_context.source == "sources/github/owner/repo"
            assert call_args.source_context.github_repo_context.starting_branch == "main"

    @pytest.mark.asyncio
    async def test_explicit_source_skips_detection(self) -> None:
        with patch("veridical.dispatcher.session.GitWrapper") as MockGitWrapper:
            # Mock GitWrapper instance
            mock_git = MagicMock()
            MockGitWrapper.return_value = mock_git

            # Mock dependencies
            config = MagicMock()
            config.git.base_branch = "main"
            client = MagicMock()
            client.create_session = AsyncMock(return_value=MagicMock())

            dispatcher = Dispatcher(config, client, repo_path=Path("/tmp"))

            # Call with explicit source
            await dispatcher.create_session("test prompt", source="sources/github/other/repo")

            # Verify GitWrapper NOT called
            mock_git.get_remote_url.assert_not_called()

            # Verify API call
            call_args = client.create_session.call_args[0][0]
            assert call_args.source_context.source == "sources/github/other/repo"
