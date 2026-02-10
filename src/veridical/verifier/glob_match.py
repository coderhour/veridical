"""Glob matching utility that supports ** for recursive directory matching."""

import re
from functools import lru_cache


@lru_cache(maxsize=256)
def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Convert a glob pattern to a compiled regex.

    Supports:
    - ``*`` matches anything except ``/``
    - ``**`` matches zero or more path segments (including ``/``)
    - ``?`` matches any single character except ``/``

    Args:
        pattern: Glob pattern string.

    Returns:
        Compiled regex pattern.
    """
    i = 0
    n = len(pattern)
    parts: list[str] = []

    while i < n:
        c = pattern[i]
        if c == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                # ** — match zero or more path segments
                i += 2
                if i < n and pattern[i] == "/":
                    i += 1
                    # **/  — zero or more directory segments followed by more pattern
                    parts.append("(?:.+/)?")
                else:
                    # ** at end of pattern — match everything remaining
                    parts.append(".*")
            else:
                # * — match anything except /
                parts.append("[^/]*")
                i += 1
        elif c == "?":
            parts.append("[^/]")
            i += 1
        else:
            parts.append(re.escape(c))
            i += 1

    return re.compile("^" + "".join(parts) + "$")


def glob_match(path: str, pattern: str) -> bool:
    """Test whether *path* matches a glob *pattern* with ``**`` support.

    Args:
        path: File path to test (forward-slash separated).
        pattern: Glob pattern (supports ``*``, ``**``, ``?``).

    Returns:
        True if the path matches the pattern.
    """
    return _glob_to_regex(pattern).match(path) is not None
