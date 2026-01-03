"""API-specific exceptions.

These are re-exported from veridical.exceptions for convenience,
but can also be imported directly from this module.
"""

from veridical.exceptions import (
    APIError,
    AuthenticationError,
    RateLimitError,
)

__all__ = ["APIError", "AuthenticationError", "RateLimitError"]
