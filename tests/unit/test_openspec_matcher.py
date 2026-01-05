from pathlib import Path

import pytest

from veridical.openspec.matcher import match_spec_from_description
from veridical.openspec.scanner import OpenSpecInfo


@pytest.fixture
def specs():
    return [
        OpenSpecInfo(
            name="add-backoff",
            path=Path("p1"),
            tasks_file=Path("t1"),
            incomplete_count=1,
            total_count=1,
        ),
        OpenSpecInfo(
            name="add-backoff-extended",
            path=Path("p2"),
            tasks_file=Path("t2"),
            incomplete_count=1,
            total_count=1,
        ),
        OpenSpecInfo(
            name="fix-logger",
            path=Path("p3"),
            tasks_file=Path("t3"),
            incomplete_count=1,
            total_count=1,
        ),
    ]


def test_match_exact_pattern(specs):
    desc = "Implement spec add-backoff"
    match = match_spec_from_description(desc, specs)
    assert match.name == "add-backoff"


def test_match_short_pattern(specs):
    desc = "implement fix-logger"
    match = match_spec_from_description(desc, specs)
    assert match.name == "fix-logger"


def test_match_fuzzy(specs):
    desc = "Working on add-backoff-extended right now"
    match = match_spec_from_description(desc, specs)
    assert match.name == "add-backoff-extended"


def test_match_fuzzy_greedy(specs):
    # Should match the longer one if both are present in text
    desc = "Implementing add-backoff and add-backoff-extended"
    match = match_spec_from_description(desc, specs)
    assert match.name == "add-backoff-extended"


def test_no_match(specs):
    desc = "Just fixing some random bugs"
    match = match_spec_from_description(desc, specs)
    assert match is None


def test_empty_input():
    assert match_spec_from_description("", []) is None
    assert match_spec_from_description("test", []) is None
