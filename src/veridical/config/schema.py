"""Configuration schema definitions using Pydantic."""

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class QualityGate(BaseModel):
    """Configuration for a single quality gate command."""

    name: str = Field(..., description="Name of the quality gate")
    command: str = Field(..., description="Command to execute")
    timeout: int = Field(300, ge=1, description="Timeout in seconds")
    required: bool = Field(True, description="Whether this gate must pass")


class JulesConfig(BaseModel):
    """Configuration for Jules API interaction."""

    api_base_url: str = Field(
        "https://jules.googleapis.com/v1alpha",
        description="Base URL for Jules API",
    )
    poll_interval: int = Field(
        30,
        ge=1,
        le=600,
        description="Polling interval in seconds",
    )
    poll_timeout: int = Field(
        3600,
        ge=60,
        description="Maximum time to wait for session completion in seconds",
    )
    auto_approve_plans: bool = Field(
        True,
        description="Automatically approve plans in autonomous mode",
    )
    max_retries: int = Field(
        3,
        ge=0,
        le=10,
        description="Maximum retry attempts for API calls",
    )
    retry_delay: float = Field(
        1.0,
        ge=0.1,
        description="Base delay between retries in seconds",
    )


class SupervisorConfig(BaseModel):
    """Configuration for the supervisor loop."""

    max_iterations: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum number of loop iterations",
    )
    max_consecutive_failures: int = Field(
        3,
        ge=1,
        description="Maximum consecutive failures before circuit break",
    )
    stagnation_threshold: int = Field(
        3,
        ge=1,
        description="Identical diff count before stagnation detection",
    )


class VerifierConfig(BaseModel):
    """Configuration for the verifier component."""

    quality_gates: list[QualityGate] = Field(
        default_factory=lambda: [
            QualityGate(name="pytest", command="pytest"),
            QualityGate(name="ruff", command="ruff check src/"),
            QualityGate(name="mypy", command="mypy src/"),
        ],
        description="List of quality gates to run",
    )
    summary_max_length: int = Field(
        2000,
        ge=100,
        description="Maximum length of error summary for feedback",
    )


class GitConfig(BaseModel):
    """Configuration for git operations."""

    base_branch: str = Field(
        "main",
        description="Base branch to create iteration branches from",
    )
    branch_prefix: str = Field(
        "veridical/iter-",
        description="Prefix for iteration branch names",
    )
    auto_cleanup: bool = Field(
        True,
        description="Automatically delete iteration branches after merge",
    )


class VeridicalConfig(BaseSettings):
    """Root configuration for Veridical.

    Configuration is loaded from:
    1. Default values
    2. .veridical.yaml file (if present)
    3. Environment variables (prefixed with VERIDICAL_)

    Environment variables override file values, which override defaults.
    """

    model_config = SettingsConfigDict(
        env_prefix="VERIDICAL_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    jules: JulesConfig = Field(default_factory=JulesConfig)
    supervisor: SupervisorConfig = Field(default_factory=SupervisorConfig)
    verifier: VerifierConfig = Field(default_factory=VerifierConfig)
    git: GitConfig = Field(default_factory=GitConfig)
