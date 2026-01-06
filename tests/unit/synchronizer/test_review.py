"""Unit tests for the ReviewManager class."""

from unittest.mock import MagicMock, patch

import pytest

from veridical.synchronizer.review import ReviewManager


@pytest.mark.unit
class TestReviewManager:
    """Tests for the ReviewManager class."""

    def test_compute_patch_hash_extracts_file_diff(self) -> None:
        """Test that patch hash is computed from the file-specific diff."""
        manager = ReviewManager()

        patch_content = """diff --git a/file1.py b/file1.py
index 1234567..890abcd 100644
--- a/file1.py
+++ b/file1.py
@@ -1,3 +1,4 @@
+new line
 existing
diff --git a/file2.py b/file2.py
index abcdef0..1234567 100644
--- a/file2.py
+++ b/file2.py
@@ -1,2 +1,3 @@
+another new line
 old line
"""

        hash1 = manager.compute_patch_hash(patch_content, "file1.py")
        hash2 = manager.compute_patch_hash(patch_content, "file2.py")

        # Different files should produce different hashes
        assert hash1 != hash2
        assert len(hash1) == 64  # SHA256 hex digest length
        assert len(hash2) == 64

    def test_compute_patch_hash_same_content_same_hash(self) -> None:
        """Test that identical diffs produce identical hashes."""
        manager = ReviewManager()

        patch = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1 +1 @@
-old
+new
"""

        hash1 = manager.compute_patch_hash(patch, "test.py")
        hash2 = manager.compute_patch_hash(patch, "test.py")

        assert hash1 == hash2

    def test_record_approval(self) -> None:
        """Test recording approval for a file."""
        manager = ReviewManager()
        patch = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
+content
"""

        manager.record_approval("test.py", patch, approved=True)

        assert "test.py" in manager._approvals
        assert manager._approvals["test.py"].approved is True

    def test_record_rejection(self) -> None:
        """Test recording rejection for a file."""
        manager = ReviewManager()
        patch = """diff --git a/test.py b/test.py
+content
"""

        manager.record_approval("test.py", patch, approved=False)

        assert "test.py" in manager._approvals
        assert manager._approvals["test.py"].approved is False

    def test_is_fully_approved_returns_true_when_all_approved(self) -> None:
        """Test that is_fully_approved returns True when all files approved."""
        manager = ReviewManager()
        patch = """diff --git a/file1.py b/file1.py
+content1
diff --git a/file2.py b/file2.py
+content2
"""

        # Approve both files
        manager.record_approval("file1.py", patch, approved=True)
        manager.record_approval("file2.py", patch, approved=True)

        assert manager.is_fully_approved(["file1.py", "file2.py"], patch)

    def test_is_fully_approved_returns_false_when_not_all_approved(self) -> None:
        """Test that is_fully_approved returns False when some files not approved."""
        manager = ReviewManager()
        patch = """diff --git a/file1.py b/file1.py
+content1
diff --git a/file2.py b/file2.py
+content2
"""

        # Only approve one file
        manager.record_approval("file1.py", patch, approved=True)

        assert not manager.is_fully_approved(["file1.py", "file2.py"], patch)

    def test_is_fully_approved_returns_false_when_content_changed(self) -> None:
        """Test that is_fully_approved returns False when file content changed."""
        manager = ReviewManager()
        original_patch = """diff --git a/test.py b/test.py
+original content
"""
        new_patch = """diff --git a/test.py b/test.py
+new content
"""

        # Approve with original content
        manager.record_approval("test.py", original_patch, approved=True)

        # Should not be approved for new content
        assert not manager.is_fully_approved(["test.py"], new_patch)

    def test_get_files_needing_review_excludes_approved(self) -> None:
        """Test that already-approved files are excluded from review."""
        manager = ReviewManager()
        patch = """diff --git a/file1.py b/file1.py
+content1
diff --git a/file2.py b/file2.py
+content2
"""

        # Approve only file1
        manager.record_approval("file1.py", patch, approved=True)

        files_needing = manager.get_files_needing_review(["file1.py", "file2.py"], patch)

        assert "file1.py" not in files_needing
        assert "file2.py" in files_needing

    def test_clear_approvals(self) -> None:
        """Test clearing all approvals."""
        manager = ReviewManager()
        patch = "+content"

        manager.record_approval("test.py", patch, approved=True)
        assert len(manager._approvals) == 1

        manager.clear_approvals()
        assert len(manager._approvals) == 0

    def test_prompt_for_review_returns_true_when_all_approved(self) -> None:
        """Test that prompt returns True immediately when all files already approved."""
        manager = ReviewManager()
        patch = """diff --git a/test.py b/test.py
+content
"""

        # Pre-approve the file
        manager.record_approval("test.py", patch, approved=True)

        # Should return True without prompting
        result = manager.prompt_for_review(["test.py"], patch)

        assert result is True

    @patch("veridical.synchronizer.review.typer.confirm")
    def test_prompt_for_review_prompts_and_records(self, mock_confirm: MagicMock) -> None:
        """Test that prompt asks user and records the decision."""
        mock_confirm.return_value = True
        manager = ReviewManager(console=MagicMock())
        patch = """diff --git a/test.py b/test.py
+content
"""

        result = manager.prompt_for_review(["test.py"], patch)

        assert result is True
        mock_confirm.assert_called_once()
        assert manager._approvals["test.py"].approved is True

    @patch("veridical.synchronizer.review.typer.confirm")
    def test_prompt_for_review_handles_rejection(self, mock_confirm: MagicMock) -> None:
        """Test that prompt handles user rejection."""
        mock_confirm.return_value = False
        manager = ReviewManager(console=MagicMock())
        patch = """diff --git a/test.py b/test.py
+content
"""

        result = manager.prompt_for_review(["test.py"], patch)

        assert result is False
        assert manager._approvals["test.py"].approved is False

    def test_extract_file_diff(self) -> None:
        """Test extracting diff for a specific file from a multi-file patch."""
        manager = ReviewManager()
        patch = """diff --git a/file1.py b/file1.py
--- a/file1.py
+++ b/file1.py
+content1
diff --git a/file2.py b/file2.py
--- a/file2.py
+++ b/file2.py
+content2
"""

        diff1 = manager._extract_file_diff(patch, "file1.py")
        diff2 = manager._extract_file_diff(patch, "file2.py")

        assert "content1" in diff1
        assert "content2" not in diff1
        assert "content2" in diff2
        assert "content1" not in diff2

    def test_empty_files_list_returns_true(self) -> None:
        """Test that empty files list returns True without prompting."""
        manager = ReviewManager()

        result = manager.prompt_for_review([], "any patch content")

        assert result is True
