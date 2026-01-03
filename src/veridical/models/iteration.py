"""Iteration tracking models for the supervisor loop."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IterationContext(BaseModel):
    """Context for a single iteration of the supervisor loop.

    Tracks the state and history of an iteration, including error context
    from previous iterations that should be fed back to the agent.
    """

    iteration_number: int = Field(..., ge=0, description="Current iteration number (0-indexed)")
    session_id: str | None = Field(None, description="Jules session ID for this iteration")
    branch_name: str | None = Field(None, description="Local git branch for this iteration")
    started_at: datetime = Field(
        default_factory=datetime.now, description="When this iteration started"
    )
    completed_at: datetime | None = Field(None, description="When this iteration completed")
    error_context: str | None = Field(
        None, description="Error context from previous iteration to feed to agent"
    )
    diff_hash: str | None = Field(
        None, description="Hash of the diff from this iteration for stagnation detection"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional iteration metadata"
    )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate the duration of this iteration in seconds."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    def with_completion(self, completed_at: datetime | None = None) -> "IterationContext":
        """Return a new context with completion timestamp set."""
        return self.model_copy(update={"completed_at": completed_at or datetime.now()})

    def with_error_context(self, error_context: str) -> "IterationContext":
        """Return a new context with error context set."""
        return self.model_copy(update={"error_context": error_context})
