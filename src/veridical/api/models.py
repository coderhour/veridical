"""Pydantic models for Jules API request/response payloads."""

from datetime import datetime
from enum import Enum

from pydantic import AliasChoices, BaseModel, Field


class SessionState(str, Enum):
    """State of a Jules session as returned by the API."""

    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PLANNING = "PLANNING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_PLAN_APPROVAL = "WAITING_FOR_PLAN_APPROVAL"
    WAITING_FOR_INPUT = "WAITING_FOR_INPUT"
    PAUSED = "PAUSED"
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
    title: str | None = Field(
        None,
        description="Human-readable title for the session",
    )
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
    state: SessionState | None = Field(None, description="Current session state")
    create_time: datetime | None = Field(
        None,
        alias="createTime",
        description="When the session was created",
    )
    update_time: datetime | None = Field(
        None,
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


class GitPatch(BaseModel):
    """A patch in Git format."""

    unidiff_patch: str | None = Field(None, alias="unidiffPatch")
    base_commit_id: str | None = Field(None, alias="baseCommitId")
    suggested_commit_message: str | None = Field(None, alias="suggestedCommitMessage")

    class Config:
        populate_by_name = True


class ChangeSet(BaseModel):
    """A set of changes to be applied to a source."""

    git_patch: GitPatch | None = Field(None, alias="gitPatch")
    source: str | None = Field(None, description="Format: sources/{source}")

    class Config:
        populate_by_name = True


class Artifact(BaseModel):
    """An artifact produced by an activity step."""

    change_set: ChangeSet | None = Field(None, alias="changeSet")
    media: dict[str, object] | None = None
    bash_output: dict[str, object] | None = Field(None, alias="bashOutput")

    class Config:
        populate_by_name = True


class ActivityEntry(BaseModel):
    """An activity log entry from a Jules session."""

    name: str | None = None
    id: str | None = None
    create_time: datetime | None = Field(
        None,
        alias="createTime",
        validation_alias=AliasChoices("createTime", "timestamp"),
    )
    type: str | None = None
    message: str | None = None
    description: str | None = None
    originator: str | None = None
    artifacts: list[Artifact] = Field(default_factory=list)

    # Union fields from discovery
    agent_messaged: dict[str, object] | None = Field(None, alias="agentMessaged")
    user_messaged: dict[str, object] | None = Field(None, alias="userMessaged")
    plan_generated: dict[str, object] | None = Field(None, alias="planGenerated")
    plan_approved: dict[str, object] | None = Field(None, alias="planApproved")
    progress_updated: dict[str, object] | None = Field(None, alias="progressUpdated")
    session_completed: dict[str, object] | None = Field(None, alias="sessionCompleted")
    session_failed: dict[str, object] | None = Field(None, alias="sessionFailed")

    class Config:
        populate_by_name = True

    @property
    def timestamp(self) -> datetime | None:
        """Alias for create_time to maintain backward compatibility if any."""
        return self.create_time


class ApprovalRequest(BaseModel):
    """Request payload for approving a session plan."""

    # Currently empty, but included for future extensibility
    pass


class SendMessageRequest(BaseModel):
    """Request payload for sending a message to a session."""

    prompt: str = Field(..., description="Prompt/message to send to the session")
