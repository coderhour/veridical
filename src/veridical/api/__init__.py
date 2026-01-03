"""API module - Jules API client and models."""

from veridical.api.client import JulesClient
from veridical.api.exceptions import APIError, AuthenticationError, RateLimitError
from veridical.api.models import (
    ActivityEntry,
    AutomationMode,
    CreateSessionRequest,
    GitHubRepoContext,
    SessionResponse,
    SessionState,
    SourceContext,
)

__all__ = [
    "APIError",
    "ActivityEntry",
    "AuthenticationError",
    "AutomationMode",
    "CreateSessionRequest",
    "GitHubRepoContext",
    "JulesClient",
    "RateLimitError",
    "SessionResponse",
    "SessionState",
    "SourceContext",
]
