"""Configuration schema definitions using Pydantic."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, root_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class QualityGate(BaseModel):
    """Configuration for a single quality gate."""

    name: str = Field(..., description="Name of the quality gate")
    type: Literal["command", "task_completion"] = Field(
        "command", description="Type of the quality gate"
    )
    command: str | None = Field(None, description="Command to execute for 'command' type gates")
    path: str | None = Field(None, description="File path for 'task_completion' type gates")
    timeout: int = Field(300, ge=1, description="Timeout in seconds")
    required: bool = Field(True, description="Whether this gate must pass")
    parallel: bool = Field(False, description="Whether this gate can run in parallel with others")

    @root_validator(skip_on_failure=True)
    def check_gate_config(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Validate gate-specific configuration."""
        gate_type = values.get("type")
        command = values.get("command")
        path = values.get("path")

        if gate_type == "command":
            if not command:
                raise ValueError("`command` is required for 'command' gate type")
            if path is not None:
                raise ValueError("`path` is not applicable for 'command' gate type")
        elif gate_type == "task_completion":
            if not path:
                raise ValueError("`path` is required for 'task_completion' gate type")
            if command is not None:
                raise ValueError("`command` is not applicable for 'task_completion' gate type")

        return values


class ConstantBackoffConfig(BaseModel):
    """Configuration for constant backoff."""

    type: Literal["constant"] = "constant"
    interval: float = Field(30.0, ge=0, description="Interval in seconds between attempts")


class ExponentialBackoffConfig(BaseModel):
    """Configuration for exponential backoff."""

    type: Literal["exponential"] = "exponential"
    base_interval: float = Field(30.0, ge=0, description="Initial interval in seconds")
    max_interval: float = Field(300.0, ge=0, description="Maximum interval cap in seconds")
    jitter_factor: float = Field(
        0.1, ge=0.0, le=1.0, description="Random jitter as fraction of interval"
    )


BackoffConfig = Annotated[
    ConstantBackoffConfig | ExponentialBackoffConfig, Field(discriminator="type")
]


class JulesConfig(BaseModel):
    """Configuration for Jules API interaction."""

    api_base_url: str = Field(
        "https://jules.googleapis.com/v1alpha",
        description="Base URL for Jules API",
    )
    backoff_strategy: Literal["constant", "exponential"] = Field(
        "constant",
        description="Strategy for polling interval backoff",
    )
    poll_interval: float = Field(
        30.0,
        ge=0,
        description="Interval in seconds between poll attempts (used for constant strategy)",
    )
    backoff: BackoffConfig = Field(
        default_factory=ConstantBackoffConfig,
        description="Detailed backoff configuration",
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


class LocalLLMConfig(BaseModel):
    """Configuration for local LLM integration."""

    base_url: str = Field(
        ...,
        description="Base URL for OpenAI-compatible local LLM endpoint (e.g., http://localhost:11434/v1)",
    )
    model: str = Field(
        ...,
        description="Model name to use for log analysis (e.g., qwen2.5:7b, llama3.2:8b)",
    )
    api_key: str | None = Field(
        None,
        description="API key for the local LLM endpoint (optional, use 'ollama' for Ollama)",
    )
    timeout: int = Field(
        30,
        ge=1,
        le=300,
        description="Timeout in seconds per LLM request",
    )
    chunk_size: int = Field(
        500,
        ge=100,
        le=2000,
        description="Number of lines per chunk for recursive summarization",
    )


class VerifierConfig(BaseModel):
    """Configuration for the verifier component."""

    quality_gates: list[QualityGate] = Field(
        default_factory=lambda: [
            QualityGate(
                name="task_completion",
                type="task_completion",
                required=True,
                path="auto",
            ),
            QualityGate(name="pytest", command="pytest"),
            QualityGate(name="ruff", command="ruff check src/"),
            QualityGate(name="mypy", command="mypy src/"),
        ],
        description="List of quality gates to run",
    )
    parallel_timeout: int = Field(
        600,
        ge=1,
        description="Timeout in seconds for parallel gate execution",
    )
    summary_max_length: int = Field(
        2000,
        ge=100,
        description="Maximum length of error summary for feedback",
    )
    local_llm: LocalLLMConfig | None = Field(
        None,
        description="Optional local LLM configuration for advanced log analysis",
    )
    feedback_mode: Literal["heuristic", "rlm", "auto"] = Field(
        "auto",
        description=(
            "Feedback generation mode. "
            "'heuristic': simple log compression. "
            "'rlm': Recursive Log-aware summarization with local LLM. "
            "'auto': use 'rlm' if log exceeds threshold, else 'heuristic'."
        ),
    )
    rlm_threshold: int = Field(
        1000,
        ge=100,
        description=(
            "Line count threshold to trigger RLM in 'auto' mode. "
            "Has no effect if mode is not 'auto'."
        ),
    )


class ScopeValidationConfig(BaseModel):
    """Configuration for patch scope validation."""

    allowlist: list[str] | None = Field(
        None,
        description="List of glob patterns for files that are allowed to be modified.",
    )
    denylist: list[str] | None = Field(
        default_factory=lambda: [
            # CI/CD configurations
            ".github/",
            ".gitlab-ci.yml",
            ".gitlab/",
            ".circleci/",
            "Jenkinsfile",
            ".travis.yml",
            "azure-pipelines.yml",
            ".buildkite/",
            # Secrets and credentials
            "*.env",
            ".env*",
            "*.pem",
            "*.key",
            "*.crt",
            "*.p12",
            "*.pfx",
            "*credentials*",
            "*secrets*",
            ".netrc",
            ".npmrc",
            ".pypirc",
            # Infrastructure and deployment
            "terraform/",
            "*.tf",
            "*.tfvars",
            "pulumi/",
            "Pulumi.yaml",
            "kubernetes/",
            "k8s/",
            "helm/",
            "docker-compose*.yml",
            "Dockerfile*",
            # Security policies and configs
            "CODEOWNERS",
            "SECURITY.md",
            ".securityrc",
            # AI agent instructions (prevent self-modification)
            "AGENTS.md",
            "CLAUDE.md",
            ".cursorrules",
            ".windsurfrules",
        ],
        description="List of glob patterns for files that are not allowed to be modified.",
    )
    reviewlist: list[str] | None = Field(
        default_factory=lambda: [
            # Package lock files (supply chain security - require human approval)
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "poetry.lock",
            "Pipfile.lock",
            "Cargo.lock",
            "Gemfile.lock",
            "composer.lock",
            "uv.lock",
            "mix.lock",
        ],
        description="List of glob patterns for files that require explicit human approval.",
    )
    strict_mode: bool = Field(
        True,
        description="If true, patches violating the scope are rejected. If false, a warning is logged.",
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
    auto_create_work_branch: bool = Field(
        True,
        description="Automatically create a work branch for changes instead of merging to base_branch",
    )
    scope_validation: ScopeValidationConfig = Field(
        default_factory=ScopeValidationConfig,
        description="Configuration for validating the scope of incoming patches.",
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
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO",
        description="Default logging level",
    )
