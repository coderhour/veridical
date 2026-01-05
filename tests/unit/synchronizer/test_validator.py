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
