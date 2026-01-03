"""Veridical - Local Supervisory Control System for Google Jules.

Veridical implements autonomous quality assurance loops that enforce high code
quality through iterative testing, linting, and spec-driven development.
"""

from importlib.metadata import version

__version__ = version("veridical")
__all__ = ["__version__"]
