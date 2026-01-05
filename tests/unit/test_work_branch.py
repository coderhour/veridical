from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from veridical.synchronizer.branch import BranchManager


@pytest.fixture
def mock_git():
    with patch("veridical.synchronizer.branch.GitWrapper") as mock:
        instance = mock.return_value
        instance.get_current_branch.return_value = "main"
        yield instance


def test_branch_manager_initialization_captures_starting_branch(mock_git):
    """Test that BranchManager captures the current branch on init."""
    manager = BranchManager(Path("/tmp/repo"), base_branch="main")
    assert manager.starting_branch == "main"
    mock_git.get_current_branch.assert_called_once()


def test_branch_manager_detached_head_fallback(mock_git):
    """Test that BranchManager falls back to base_branch on detached HEAD."""
    mock_git.get_current_branch.return_value = None
    manager = BranchManager(Path("/tmp/repo"), base_branch="develop")
    assert manager.starting_branch == "develop"


def test_create_work_branch_new(mock_git):
    """Test creating a work branch that doesn't exist."""
    mock_git.branch_exists.return_value = False
    manager = BranchManager(Path("/tmp/repo"), base_branch="main")

    branch_name = manager.create_work_branch("New Feature")

    assert branch_name == "feat/new-feature"
    mock_git.checkout.assert_any_call("main")
    mock_git.checkout.assert_any_call("feat/new-feature", create=True)


def test_create_work_branch_exists(mock_git):
    """Test checking out an existing work branch."""
    mock_git.branch_exists.return_value = True
    manager = BranchManager(Path("/tmp/repo"), base_branch="main")

    branch_name = manager.create_work_branch("Existing Fix", prefix="fix")

    assert branch_name == "fix/existing-fix"
    mock_git.checkout.assert_called_with("fix/existing-fix")
    # Should not checkout base_branch if it already exists
    assert MagicMock(method="checkout", args=("main",)) not in mock_git.method_calls
