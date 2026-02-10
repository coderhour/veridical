"""Data models for the Worker abstraction layer."""

from enum import Enum, auto
from typing import Any

from pydantic import BaseModel, Field


class WorkStatus(Enum):
    """Status of a dispatched work item."""

    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()


class WorkHandle(BaseModel):
    """Opaque handle returned by Worker.dispatch().

    The supervisor passes this to poll() and sync() without
    inspecting its internals. Each worker backend stores
    whatever identifiers it needs.
    """

    backend: str = Field(..., description="Worker backend name (e.g. 'jules', 'local')")
    handle_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Backend-specific data (e.g. session_id for Jules)",
    )


class WorkResult(BaseModel):
    """Result of Worker.dispatch()."""

    handle: WorkHandle = Field(..., description="Handle for polling and syncing")
    dispatched: bool = Field(True, description="Whether work was successfully dispatched")
    error: str | None = Field(None, description="Error message if dispatch failed")


class PollResult(BaseModel):
    """Result of Worker.poll()."""

    status: WorkStatus = Field(..., description="Current status of the work")
    error: str | None = Field(None, description="Error message if work failed")


class SyncResult(BaseModel):
    """Result of Worker.sync()."""

    success: bool = Field(..., description="Whether sync was successful")
    iter_branch: str | None = Field(None, description="Iteration branch name if applicable")
    diff_hash: str | None = Field(
        None, description="Hash of the applied diff for stagnation detection"
    )
    patch_summary: str | None = Field(None, description="Human-readable summary of the patch")
    review_required_files: list[str] | None = Field(
        None, description="Files requiring human review"
    )
    needs_human_review: bool = Field(
        False, description="Whether human review is needed before proceeding"
    )
    error: str | None = Field(None, description="Error message if sync failed")


class WorkerConfig(BaseModel):
    """Base configuration for worker backends.

    Each worker backend can extend this with its own fields.
    """

    backend: str = Field(
        "jules",
        description="Worker backend name (e.g. 'jules', 'local')",
    )
    backend_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Backend-specific configuration passed to the worker constructor",
    )
