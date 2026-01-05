import pytest

from veridical.synchronizer.branch import sanitize_branch_name


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Simple Name", "simple-name"),
        ("Already-hyphenated", "already-hyphenated"),
        ("With_Underscores", "with-underscores"),
        ("Special! characters? Here.", "special-characters-here"),
        ("Multiple   Spaces", "multiple-spaces"),
        ("---Leading and trailing---", "leading-and-trailing"),
        ("123 Numbers work", "123-numbers-work"),
        ("", "veridical-work"),
        ("!!!", "veridical-work"),
        ("Mixed CASE-and_symbols", "mixed-case-and-symbols"),
        ("Version 2.0.1", "version-201"),
    ],
)
def test_sanitize_branch_name(name, expected):
    """Test branch name sanitization logic."""
    assert sanitize_branch_name(name) == expected
