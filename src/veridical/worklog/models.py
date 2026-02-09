"""Work log entry model."""

from datetime import datetime

from pydantic import BaseModel, Field


class WorkLogEntry(BaseModel):
    """Represents a single iteration entry in the work log.

    This model captures the complete context of a supervisor iteration,
    including inputs (task description, error context, prompt) and outputs
    (session status, verification results, duration).
    """

    timestamp: datetime = Field(default_factory=datetime.now)
    iteration: int
    session_id: str
    task_description: str
    error_context: str | None = None
    prompt_sent: str | None = None
    session_status: str = "unknown"
    verification_passed: bool | None = None
    verification_errors: str | None = None
    duration_seconds: float | None = None
