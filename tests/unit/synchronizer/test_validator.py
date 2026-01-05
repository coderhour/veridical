"""Unit tests for the ScopeValidator."""

import pytest

from veridical.config.schema import ScopeValidationConfig
from veridical.synchronizer.validator import ScopeValidator

# Sample patch data for testing
PATCH_DATA_VALID = """
--- a/src/main.py
+++ b/src/main.py
@@ -1,1 +1,2 @@
 def main():
+    print("Hello, world!")
"""

PATCH_DATA_DENYLISTED = """
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -1,1 +1,2 @@
-This is an agent instruction file.
+This is a modified agent instruction file.
"""

PATCH_DATA_NOT_IN_ALLOWLIST = """
--- a/src/config.py
+++ b/src/config.py
@@ -1,1 +1,2 @@
 class Config:
+    SECRET_KEY = "supersecret"
"""

PATCH_DATA_MIXED = """
--- a/src/main.py
+++ b/src/main.py
@@ -1,1 +1,2 @@
 def main():
+    print("Hello, world!")
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -1,1 +1,2 @@
-name: CI
+name: Continuous Integration
"""


@pytest.fixture
def default_config() -> ScopeValidationConfig:
    """Default config with denylist."""
    return ScopeValidationConfig()


def test_validate_patch_valid(default_config: ScopeValidationConfig):
    """Test that a valid patch passes validation."""
    validator = ScopeValidator(default_config)
    result = validator.validate_patch(PATCH_DATA_VALID)
    assert result.is_valid
    assert not result.violations


def test_validate_patch_denylisted(default_config: ScopeValidationConfig):
    """Test that a patch modifying a denylisted file fails."""
    validator = ScopeValidator(default_config)
    result = validator.validate_patch(PATCH_DATA_DENYLISTED)
    assert not result.is_valid
    assert len(result.violations) == 1
    assert "AGENTS.md" in result.violations[0]
    assert "denied by denylist" in result.violations[0]


def test_validate_patch_allowlist_pass():
    """Test that a patch passes when it matches the allowlist."""
    config = ScopeValidationConfig(allowlist=["src/*.py"])
    validator = ScopeValidator(config)
    result = validator.validate_patch(PATCH_DATA_VALID)
    assert result.is_valid


def test_validate_patch_allowlist_fail():
    """Test that a patch fails when it does not match the allowlist."""
    config = ScopeValidationConfig(allowlist=["src/utils.py"])
    validator = ScopeValidator(config)
    result = validator.validate_patch(PATCH_DATA_VALID)
    assert not result.is_valid
    assert len(result.violations) == 1
    assert "src/main.py" in result.violations[0]
    assert "not in allowlist" in result.violations[0]


def test_validate_patch_mixed_violations(default_config: ScopeValidationConfig):
    """Test a patch with both valid and denylisted file modifications."""
    validator = ScopeValidator(default_config)
    result = validator.validate_patch(PATCH_DATA_MIXED)
    assert not result.is_valid
    assert len(result.violations) == 1
    assert ".github/workflows/ci.yml" in result.violations[0]


def test_parse_modified_files():
    """Test parsing of file paths from a diff."""
    validator = ScopeValidator(ScopeValidationConfig())
    files = validator._parse_modified_files(PATCH_DATA_MIXED)
    assert files == {"src/main.py", ".github/workflows/ci.yml"}


def test_empty_patch_is_valid(default_config: ScopeValidationConfig):
    """Test that an empty or whitespace-only patch is always valid."""
    validator = ScopeValidator(default_config)
    result = validator.validate_patch("   ")
    assert result.is_valid


# --- Reviewlist Tests ---

PATCH_DATA_LOCK_FILE = """
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,1 +1,2 @@
 {
+  "name": "test"
"""

PATCH_DATA_POETRY_LOCK = """
--- a/poetry.lock
+++ b/poetry.lock
@@ -1,1 +1,2 @@
 [[package]]
+name = "test"
"""

PATCH_DATA_MIXED_WITH_LOCK = """
--- a/src/main.py
+++ b/src/main.py
@@ -1,1 +1,2 @@
 def main():
+    print("Hello, world!")
--- a/yarn.lock
+++ b/yarn.lock
@@ -1,1 +1,2 @@
 # yarn lockfile v1
+test@1.0.0:
"""

PATCH_DATA_LOCK_AND_DENIED = """
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,1 +1,2 @@
 {
+  "name": "test"
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -1,1 +1,2 @@
-name: CI
+name: Continuous Integration
"""


def test_validate_patch_reviewlist_triggers_review(default_config: ScopeValidationConfig):
    """Test that a patch modifying a reviewlist file requires review."""
    validator = ScopeValidator(default_config)
    result = validator.validate_patch(PATCH_DATA_LOCK_FILE)
    assert result.is_valid  # Not a violation, but needs review
    assert len(result.review_required) == 1
    assert "package-lock.json" in result.review_required


def test_validate_patch_reviewlist_poetry_lock(default_config: ScopeValidationConfig):
    """Test that poetry.lock triggers review requirement."""
    validator = ScopeValidator(default_config)
    result = validator.validate_patch(PATCH_DATA_POETRY_LOCK)
    assert result.is_valid
    assert len(result.review_required) == 1
    assert "poetry.lock" in result.review_required


def test_validate_patch_mixed_with_reviewlist(default_config: ScopeValidationConfig):
    """Test patch with both valid files and reviewlist files."""
    validator = ScopeValidator(default_config)
    result = validator.validate_patch(PATCH_DATA_MIXED_WITH_LOCK)
    assert result.is_valid  # Valid but needs review
    assert len(result.review_required) == 1
    assert "yarn.lock" in result.review_required
    assert not result.violations


def test_validate_patch_denylist_takes_precedence_over_reviewlist(
    default_config: ScopeValidationConfig,
):
    """Test that denylist violations are reported even when reviewlist files are present."""
    validator = ScopeValidator(default_config)
    result = validator.validate_patch(PATCH_DATA_LOCK_AND_DENIED)
    assert not result.is_valid  # Denied file makes it invalid
    assert len(result.violations) == 1
    assert ".github/workflows/ci.yml" in result.violations[0]
    # Review required is still populated for the lock file
    assert "package-lock.json" in result.review_required


def test_validate_patch_custom_reviewlist():
    """Test with custom reviewlist patterns."""
    config = ScopeValidationConfig(
        denylist=[],  # Clear defaults for test
        reviewlist=["*.config.js", "config/"],
    )
    validator = ScopeValidator(config)

    # Test glob pattern
    patch_config_js = """
--- a/webpack.config.js
+++ b/webpack.config.js
@@ -1 +1,2 @@
 module.exports = {};
+// comment
"""
    result = validator.validate_patch(patch_config_js)
    assert result.is_valid
    assert "webpack.config.js" in result.review_required

    # Test directory pattern
    patch_config_dir = """
--- a/config/settings.yaml
+++ b/config/settings.yaml
@@ -1 +1,2 @@
 key: value
+key2: value2
"""
    result = validator.validate_patch(patch_config_dir)
    assert result.is_valid
    assert "config/settings.yaml" in result.review_required


def test_validate_patch_empty_reviewlist():
    """Test that empty reviewlist means no files require review."""
    config = ScopeValidationConfig(
        denylist=[],
        reviewlist=[],
    )
    validator = ScopeValidator(config)
    result = validator.validate_patch(PATCH_DATA_LOCK_FILE)
    assert result.is_valid
    assert not result.review_required


def test_validate_patch_none_reviewlist():
    """Test that None reviewlist means no files require review."""
    config = ScopeValidationConfig(
        denylist=[],
        reviewlist=None,
    )
    validator = ScopeValidator(config)
    result = validator.validate_patch(PATCH_DATA_LOCK_FILE)
    assert result.is_valid
    assert not result.review_required


def test_validate_patch_all_default_lock_files():
    """Test that all default lock files trigger review."""
    default_config = ScopeValidationConfig()
    validator = ScopeValidator(default_config)

    lock_files = [
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "Pipfile.lock",
        "Cargo.lock",
        "Gemfile.lock",
        "composer.lock",
    ]

    for lock_file in lock_files:
        patch = f"""
--- a/{lock_file}
+++ b/{lock_file}
@@ -1 +1,2 @@
 content
+more content
"""
        result = validator.validate_patch(patch)
        assert result.is_valid, f"{lock_file} should not be denied"
        assert lock_file in result.review_required, f"{lock_file} should require review"


def test_validate_patch_multiple_reviewlist_files():
    """Test patch modifying multiple reviewlist files."""
    default_config = ScopeValidationConfig()
    validator = ScopeValidator(default_config)

    patch = """
--- a/package-lock.json
+++ b/package-lock.json
@@ -1 +1,2 @@
 {
+  "test": true
--- a/yarn.lock
+++ b/yarn.lock
@@ -1 +1,2 @@
 # yarn lockfile
+test@1.0.0:
"""
    result = validator.validate_patch(patch)
    assert result.is_valid
    assert len(result.review_required) == 2
    assert "package-lock.json" in result.review_required
    assert "yarn.lock" in result.review_required
