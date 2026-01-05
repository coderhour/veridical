"""Unit tests for the PatchApplier."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from veridical.config.schema import ScopeValidationConfig
from veridical.models.result import PatchStatus
from veridical.synchronizer.patch import PatchApplier

PATCH_DATA = "diff --git a/file.txt b/file.txt\n--- a/file.txt\n+++ b/file.txt\n@@ -1 +1 @@\n-hello\n+world"
PATCH_DATA_DENYLISTED = "diff --git a/AGENTS.md b/AGENTS.md\n--- a/AGENTS.md\n+++ b/AGENTS.md\n@@ -1 +1 @@\n-old\n+new"


@patch("subprocess.run")
@patch("veridical.synchronizer.patch.GitWrapper")
def test_apply_patch_success(mock_git_wrapper, mock_run, tmp_path: Path):
    """Test successful patch application."""
    mock_git = mock_git_wrapper.return_value
    mock_git.get_diff_stat.return_value = ["file.txt"]
    mock_git.compute_diff_hash.return_value = "12345"  # Mock the final hash directly

    mock_run.return_value = MagicMock(check_returncode=lambda: None)

    patch_applier = PatchApplier(tmp_path, ScopeValidationConfig())
    result = patch_applier.apply_patch(PATCH_DATA)

    assert result.success
    assert result.status == PatchStatus.APPLIED
    assert result.files_changed == ["file.txt"]
    assert result.diff_hash == "12345"
    mock_run.assert_called_once()


def test_apply_patch_denylisted_strict(tmp_path: Path):
    """Test that a denylisted patch is rejected in strict mode."""
    config = ScopeValidationConfig(strict_mode=True)
    patch_applier = PatchApplier(tmp_path, config)
    result = patch_applier.apply_patch(PATCH_DATA_DENYLISTED)

    assert not result.success
    assert result.status == PatchStatus.REJECTED
    assert "denied by denylist" in result.error


@patch("subprocess.run")
@patch("veridical.synchronizer.patch.GitWrapper")
def test_apply_patch_denylisted_non_strict(mock_git_wrapper, mock_run, tmp_path: Path, caplog):
    """Test that a denylisted patch is warned but applied in non-strict mode."""
    mock_git = mock_git_wrapper.return_value
    mock_git.get_diff_stat.return_value = ["AGENTS.md"]
    mock_git.compute_diff_hash.return_value = "abcde"  # Mock the final hash directly

    config = ScopeValidationConfig(strict_mode=False)
    patch_applier = PatchApplier(tmp_path, config)
    result = patch_applier.apply_patch(PATCH_DATA_DENYLISTED)

    assert result.success
    assert result.status == PatchStatus.APPLIED
    assert result.diff_hash == "abcde"
    assert "Scope violations found (non-strict mode)" in caplog.text
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_apply_patch_conflict(mock_run, tmp_path: Path):
    """Test patch application with a conflict."""
    mock_run.side_effect = subprocess.CalledProcessError(1, "git apply", stderr="conflict")
    patch_applier = PatchApplier(tmp_path, ScopeValidationConfig())
    result = patch_applier.apply_patch(PATCH_DATA)

    assert not result.success
    assert result.status == PatchStatus.CONFLICT
    assert "conflict" in result.error


def test_apply_empty_patch(tmp_path: Path):
    """Test that an empty patch is a no-op."""
    patch_applier = PatchApplier(tmp_path, ScopeValidationConfig())
    result = patch_applier.apply_patch(" ")

    assert result.success
    assert result.status == PatchStatus.APPLIED
    assert not result.files_changed
