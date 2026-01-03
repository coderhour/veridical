"""Placeholder tests to verify pytest discovery."""

import pytest


@pytest.mark.unit
def test_placeholder_passes() -> None:
    """Placeholder test to verify pytest is working."""
    assert True


@pytest.mark.unit
def test_veridical_imports() -> None:
    """Verify that veridical package can be imported."""
    import veridical

    assert hasattr(veridical, "__version__")
