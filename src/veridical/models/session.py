"""Session-related models for tracking Jules sessions."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Status of a Jules session.

    Maps to the states returned by the Jules API.
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_FOR_PLAN_APPROVAL = "WAITING_FOR_PLAN_APPROVAL"
    WAITING_FOR_INPUT = "WAITING_FOR_INPUT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    def is_terminal(self) -> bool:
        """Check if this is a terminal state."""
        return self in (SessionStatus.COMPLETED, SessionStatus.FAILED)

    def is_waiting(self) -> bool:
        """Check if this state requires user input."""
        return self in (
            SessionStatus.WAITING_FOR_PLAN_APPROVAL,
            SessionStatus.WAITING_FOR_INPUT,
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
