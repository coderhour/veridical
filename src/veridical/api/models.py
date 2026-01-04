"""Pydantic models for Jules API request/response payloads."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SessionState(str, Enum):
    """State of a Jules session as returned by the API."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_FOR_PLAN_APPROVAL = "WAITING_FOR_PLAN_APPROVAL"
    WAITING_FOR_INPUT = "WAITING_FOR_INPUT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AutomationMode(str, Enum):
    """Automation mode for Jules sessions."""

    AUTO_CREATE_PR = "AUTO_CREATE_PR"
    MANUAL = "MANUAL"


class GitHubRepoContext(BaseModel):
    """GitHub repository context for session creation."""

    starting_branch: str = Field(
        "main",
        alias="startingBranch",
        description="Branch to start work from",
    )

    class Config:
        """Pydantic configuration."""

        populate_by_name = True


class SourceContext(BaseModel):
    """Source context for session creation."""

    source: str = Field(
        ...,
        description="Source identifier (e.g., 'sources/github/owner/repo')",
    )
    github_repo_context: GitHubRepoContext = Field(
        default_factory=GitHubRepoContext,
        alias="githubRepoContext",
    )

    class Config:
        """Pydantic configuration."""

        populate_by_name = True

    @classmethod
    def from_remote_url(cls, remote_url: str, branch: str = "main") -> "SourceContext":
        """Create SourceContext from a git remote URL.

        Handles both HTTPS and SSH formats:
        - https://github.com/owner/repo.git
        - git@github.com:owner/repo.git

        Args:
            remote_url: Git remote URL
            branch: Starting branch name

        Returns:
            SourceContext instance

        Raises:
            ValueError: If URL format is invalid or not GitHub
        """
        url = remote_url.removesuffix(".git")

        if "github.com" not in url:
            raise ValueError(f"Only GitHub repos are supported: {remote_url}")

        if url.startswith("https://"):
            # https://github.com/owner/repo
            path = url.split("github.com/")[-1]
        elif "git@" in url:
            # git@github.com:owner/repo
            path = url.split(":")[-1]
        else:
            raise ValueError(f"Unsupported URL format: {remote_url}")

        owner, repo = path.split("/")[-2:]  # Handle trailing slashes if any
        source = f"sources/github/{owner}/{repo}"

        return cls(
            source=source,
            github_repo_context=GitHubRepoContext(starting_branch=branch),
        )


class CreateSessionRequest(BaseModel):
    """Request payload for creating a new Jules session."""

    prompt: str = Field(..., description="Task description for Jules")
    source_context: SourceContext = Field(
        ...,
        alias="sourceContext",
        description="Repository context",
    )
    automation_mode: AutomationMode = Field(
        AutomationMode.AUTO_CREATE_PR,
        alias="automationMode",
        description="How to handle the result",
    )
    require_plan_approval: bool = Field(
        False,
        alias="requirePlanApproval",
        description="Whether to wait for plan approval",
    )

    class Config:
        """Pydantic configuration."""

        populate_by_name = True

    def model_dump_api(self) -> dict[str, object]:
        """Dump model for API request using camelCase keys."""
        return self.model_dump(by_alias=True, mode="json")


class SessionResponse(BaseModel):
    """Response from Jules API for session operations."""

    name: str = Field(..., description="Session resource name (acts as ID)")
    state: SessionState = Field(..., description="Current session state")
    create_time: datetime = Field(
        ...,
        alias="createTime",
        description="When the session was created",
    )
    update_time: datetime = Field(
        ...,
        alias="updateTime",
        description="When the session was last updated",
    )
    error_message: str | None = Field(
        None,
        alias="errorMessage",
        description="Error message if session failed",
    )

    class Config:
        """Pydantic configuration."""

        populate_by_name = True

    @property
    def session_id(self) -> str:
        """Extract session ID from resource name."""
        # name format: "sessions/{session_id}"
        return self.name.split("/")[-1]


class ActivityEntry(BaseModel):
    """An activity log entry from a Jules session."""

    timestamp: datetime = Field(..., description="When the activity occurred")
    type: str = Field(..., description="Type of activity")
    message: str = Field("", description="Activity message or content")
    metadata: dict[str, object] = Field(
        default_factory=dict,
        description="Additional activity metadata",
    )


class ApprovalRequest(BaseModel):
    """Request payload for approving a session plan."""

    # Currently empty, but included for future extensibility
    pass


class SendMessageRequest(BaseModel):
    """Request payload for sending a message to a session."""

    message: str = Field(..., description="Message to send to the session")
