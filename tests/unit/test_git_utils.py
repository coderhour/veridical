"""Tests for git utilities."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from veridical.cli.git_utils import (
    GitCheckResult,
    check_spec_status,
    format_spec_warning,
)


@pytest.mark.unit
class TestGitCheckResult:
    def test_needs_attention_with_uncommitted(self) -> None:
        """Test that needs_attention returns True when there are uncommitted changes."""
        result = GitCheckResult(has_uncommitted=True, uncommitted_files=["test.md"])
        assert result.needs_attention is True

    def test_needs_attention_with_unpushed(self) -> None:
        """Test that needs_attention returns True when there are unpushed commits."""
        result = GitCheckResult(has_unpushed=True, unpushed_commits=2)
        assert result.needs_attention is True

    def test_needs_attention_with_both(self) -> None:
        """Test that needs_attention returns True when there are both uncommitted and unpushed."""
        result = GitCheckResult(
            has_uncommitted=True,
            has_unpushed=True,
            uncommitted_files=["test.md"],
            unpushed_commits=1,
        )
        assert result.needs_attention is True

    def test_needs_attention_clean(self) -> None:
        """Test that needs_attention returns False when everything is clean."""
        result = GitCheckResult()
        assert result.needs_attention is False


@pytest.mark.unit
class TestCheckSpecStatus:
    @patch("veridical.cli.git_utils.subprocess.run")
    def test_clean_repo(self, mock_run: MagicMock) -> None:
        """Test check_spec_status with a clean repository."""
        # Mock git status --porcelain (no changes)
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        result = check_spec_status(repo_path=Path("/tmp"))

        assert result.has_uncommitted is False
        assert result.has_unpushed is False
        assert result.needs_attention is False
        assert len(result.uncommitted_files) == 0

    @patch("veridical.cli.git_utils.subprocess.run")
    @patch("veridical.cli.git_utils.Path.exists")
    def test_uncommitted_changes(self, mock_exists: MagicMock, mock_run: MagicMock) -> None:
        """Test check_spec_status with uncommitted changes."""
        # Mock path exists
        mock_exists.return_value = True

        def side_effect(*args, **kwargs):  # noqa: ARG001
            cmd = args[0]
            if "status" in cmd and "--porcelain" in cmd:
                # Git status shows modified file
                return MagicMock(returncode=0, stdout=" M openspec/project.md\n")
            elif "rev-parse" in cmd and "--abbrev-ref" in cmd and "HEAD" in cmd:
                # Current branch
                return MagicMock(returncode=0, stdout="main\n")
            elif "rev-parse" in cmd and "@{upstream}" in cmd:
                # Upstream exists
                return MagicMock(returncode=0, stdout="origin/main\n")
            elif "log" in cmd:
                # No unpushed commits
                return MagicMock(returncode=0, stdout="")
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = side_effect

        result = check_spec_status(repo_path=Path("/tmp"))

        assert result.has_uncommitted is True
        assert result.uncommitted_files == ["openspec/project.md"]
        assert result.needs_attention is True

    @patch("veridical.cli.git_utils.subprocess.run")
    def test_unpushed_commits(self, mock_run: MagicMock) -> None:
        """Test check_spec_status with unpushed commits."""

        def side_effect(*args, **kwargs):  # noqa: ARG001
            cmd = args[0]
            if "status" in cmd and "--porcelain" in cmd:
                # No uncommitted changes
                return MagicMock(returncode=0, stdout="")
            elif "rev-parse" in cmd and "--abbrev-ref" in cmd and "HEAD" in cmd:
                # Current branch
                return MagicMock(returncode=0, stdout="main\n")
            elif "rev-parse" in cmd and "@{upstream}" in cmd:
                # Upstream exists
                return MagicMock(returncode=0, stdout="origin/main\n")
            elif "log" in cmd:
                # Two unpushed commits
                return MagicMock(
                    returncode=0,
                    stdout="abc123 Add feature\ndef456 Fix bug\n",
                )
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = side_effect

        result = check_spec_status(repo_path=Path("/tmp"))

        assert result.has_unpushed is True
        assert result.unpushed_commits == 2
        assert result.needs_attention is True

    @patch("veridical.cli.git_utils.subprocess.run")
    def test_no_upstream_configured(self, mock_run: MagicMock) -> None:
        """Test check_spec_status when no upstream is configured."""

        def side_effect(*args, **kwargs):  # noqa: ARG001
            cmd = args[0]
            if "status" in cmd and "--porcelain" in cmd:
                return MagicMock(returncode=0, stdout="")
            elif "rev-parse" in cmd and "--abbrev-ref" in cmd and "HEAD" in cmd:
                return MagicMock(returncode=0, stdout="main\n")
            elif "rev-parse" in cmd and "@{upstream}" in cmd:
                # No upstream configured
                return MagicMock(returncode=1, stdout="")
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = side_effect

        result = check_spec_status(repo_path=Path("/tmp"))

        # Should not error, just return clean result
        assert result.has_unpushed is False

    @patch("veridical.cli.git_utils.subprocess.run")
    @patch("veridical.cli.git_utils.Path.exists")
    def test_multiple_uncommitted_files(self, mock_exists: MagicMock, mock_run: MagicMock) -> None:
        """Test check_spec_status with multiple uncommitted files."""
        # Mock path exists
        mock_exists.return_value = True

        def side_effect(*args, **kwargs):  # noqa: ARG001
            cmd = args[0]
            if "status" in cmd and "--porcelain" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=" M openspec/project.md\nA  openspec/new.md\n",
                )
            elif "rev-parse" in cmd and "--abbrev-ref" in cmd and "HEAD" in cmd:
                return MagicMock(returncode=0, stdout="main\n")
            elif "rev-parse" in cmd and "@{upstream}" in cmd:
                return MagicMock(returncode=0, stdout="origin/main\n")
            elif "log" in cmd:
                return MagicMock(returncode=0, stdout="")
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = side_effect

        result = check_spec_status(repo_path=Path("/tmp"))

        assert result.has_uncommitted is True
        assert len(result.uncommitted_files) == 2
        assert "openspec/project.md" in result.uncommitted_files
        assert "openspec/new.md" in result.uncommitted_files


@pytest.mark.unit
class TestFormatSpecWarning:
    def test_format_uncommitted_only(self) -> None:
        """Test formatting warning for uncommitted changes only."""
        result = GitCheckResult(
            has_uncommitted=True,
            uncommitted_files=["openspec/project.md"],
        )

        warning = format_spec_warning(result)

        assert "Uncommitted spec changes detected" in warning
        assert "openspec/project.md" in warning
        assert "git push" in warning
        assert "Unpushed spec commits" not in warning

    def test_format_unpushed_only(self) -> None:
        """Test formatting warning for unpushed commits only."""
        result = GitCheckResult(has_unpushed=True, unpushed_commits=3)

        warning = format_spec_warning(result)

        assert "Unpushed spec commits detected" in warning
        assert "3 commit(s)" in warning
        assert "git push" in warning
        assert "Uncommitted spec changes" not in warning

    def test_format_both(self) -> None:
        """Test formatting warning for both uncommitted and unpushed."""
        result = GitCheckResult(
            has_uncommitted=True,
            has_unpushed=True,
            uncommitted_files=["openspec/project.md", "openspec/spec.md"],
            unpushed_commits=2,
        )

        warning = format_spec_warning(result)

        assert "Uncommitted spec changes detected" in warning
        assert "Unpushed spec commits detected" in warning
        assert "openspec/project.md" in warning
        assert "2 commit(s)" in warning

    def test_format_many_files(self) -> None:
        """Test formatting warning with many uncommitted files (should truncate)."""
        files = [f"openspec/file{i}.md" for i in range(10)]
        result = GitCheckResult(has_uncommitted=True, uncommitted_files=files)

        warning = format_spec_warning(result)

        # Should show first 5 files
        assert "openspec/file0.md" in warning
        assert "openspec/file4.md" in warning
        # Should indicate there are more
        assert "and 5 more files" in warning
        # Should not show all files
        assert "openspec/file9.md" not in warning

    def test_format_clean(self) -> None:
        """Test formatting warning for clean repo (should be empty)."""
        result = GitCheckResult()

        warning = format_spec_warning(result)

        assert warning == ""
