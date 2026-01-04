"""Session-related models for tracking Jules sessions."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Status of a Jules session.

    Maps to the states returned by the Jules API.
    """

    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    AWAITING_PLAN_APPROVAL = "AWAITING_PLAN_APPROVAL"
    AWAITING_USER_FEEDBACK = "AWAITING_USER_FEEDBACK"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    def is_terminal(self) -> bool:
        """Check if this is a terminal state."""
        return self in (SessionStatus.COMPLETED, SessionStatus.FAILED)

    def is_waiting(self) -> bool:
        """Check if this state requires user input."""
        return self in (
            SessionStatus.AWAITING_PLAN_APPROVAL,
            SessionStatus.AWAITING_USER_FEEDBACK,
        )


class SessionInfo(BaseModel):
    """Information about a Jules session.

    Tracks the current state and metadata of a remote Jules session.
    """

    session_id: str = Field(..., description="Unique identifier for the session")
    status: SessionStatus = Field(..., description="Current session status")
    created_at: datetime = Field(
        default_factory=datetime.now, description="When the session was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="When the session was last updated"
    )
    branch: str | None = Field(None, description="Git branch the session is working on")
    prompt: str | None = Field(None, description="Original prompt sent to Jules")
    error_message: str | None = Field(None, description="Error message if session failed")

    class Config:
        """Pydantic configuration."""

        use_enum_values = False
