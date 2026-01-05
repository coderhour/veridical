import re

from .scanner import OpenSpecInfo


def match_spec_from_description(description: str, specs: list[OpenSpecInfo]) -> OpenSpecInfo | None:
    """
    Attempts to match a spec from a task description.

    Priority:
    1. Pattern: "implement spec <name>"
    2. Pattern: "implement <name>"
    3. Fuzzy match: check if any spec name appears in description
    """
    if not description or not specs:
        return None

    description_lower = description.lower()

    # Pattern 1: "implement spec <name>"
    if match := re.search(r"implement spec (\S+)", description_lower):
        spec_name = match.group(1).rstrip(",.!")
        for spec in specs:
            if spec.name == spec_name:
                return spec

    # Pattern 2: "implement <name>"
    if match := re.search(r"implement (\S+)", description_lower):
        spec_name = match.group(1).rstrip(",.!")
        # Avoid matching "something" in "implement something"
        for spec in specs:
            if spec.name == spec_name:
                return spec

    # Pattern 3: Look for any spec name in the description
    # Longer names first to avoid partial matches (e.g., matching 'foo' when 'foo-bar' is present)
    sorted_specs = sorted(specs, key=lambda x: len(x.name), reverse=True)
    for spec in sorted_specs:
        if spec.name in description_lower:
            return spec

    return None
