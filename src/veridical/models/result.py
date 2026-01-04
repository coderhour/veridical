"""Result models for operations in Veridical."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LoopResult(BaseModel):
    """Result of a complete supervisor loop run.

    Captures whether the loop succeeded, how many iterations it took,
    and any relevant error information.
    """

    success: bool = Field(..., description="Whether the loop completed successfully")
    iterations: int = Field(..., ge=0, description="Number of iterations performed")
    started_at: datetime = Field(..., description="When the loop started")
    completed_at: datetime = Field(..., description="When the loop completed")
    final_commit: str | None = Field(None, description="Git commit hash of successful result")
    failure_reason: str | None = Field(None, description="Reason for failure if not successful")
    error_context: str | None = Field(None, description="Last error context if failed")

    @property
    def duration_seconds(self) -> float:
        """Calculate the total duration of the loop in seconds."""
        return (self.completed_at - self.started_at).total_seconds()

    @classmethod
    def success_result(
        cls,
        iterations: int,
        started_at: datetime,
        final_commit: str,
    ) -> "LoopResult":
        """Create a successful result."""
        return cls(
            success=True,
            iterations=iterations,
            started_at=started_at,
            completed_at=datetime.now(),
            final_commit=final_commit,
        )

    @classmethod
    def failure_result(
        cls,
        iterations: int,
        started_at: datetime,
        failure_reason: str,
        error_context: str | None = None,
    ) -> "LoopResult":
        """Create a failure result."""
        return cls(
            success=False,
            iterations=iterations,
            started_at=started_at,
            completed_at=datetime.now(),
            failure_reason=failure_reason,
            error_context=error_context,
        )


class GateStatus(str, Enum):
    """Status of a quality gate execution."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class GateResult(BaseModel):
    """Result of a single quality gate execution.

    Captures the outcome of running a quality gate,
    including output for debugging.
    """

    name: str = Field(..., description="Name of the quality gate")
    status: GateStatus = Field(..., description="Status of the gate execution")
    command: str | None = Field(None, description="Command that was executed")
    exit_code: int | None = Field(None, description="Exit code of the command")
    output: str = Field("", description="stdout from the command")
    error_output: str = Field("", description="stderr from the command")
    duration_seconds: float = Field(..., ge=0, description="Execution time in seconds")

    @property
    def passed(self) -> bool:
        """Check if the gate passed."""
        return self.status == GateStatus.PASSED


class VerificationResult(BaseModel):
    """Result of running all quality gates.

    Aggregates results from all configured quality gates.
    """

    passed: bool = Field(..., description="Whether all gates passed")
    gates: list[GateResult] = Field(default_factory=list, description="Results for each gate")
    duration_seconds: float = Field(..., ge=0, description="Total execution time in seconds")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When verification was run"
    )

    @property
    def failed_gates(self) -> list[GateResult]:
        """Get list of gates that failed."""
        return [g for g in self.gates if not g.passed]

    @property
    def failed_gate_names(self) -> list[str]:
        """Get names of gates that failed."""
        return [g.name for g in self.failed_gates]


class PatchStatus(str, Enum):
    """Status of a patch application."""

    APPLIED = "applied"
    FAILED = "failed"
    CONFLICT = "conflict"


class PatchResult(BaseModel):
    """Result of applying a patch from Jules.

    Captures whether the patch was applied successfully and
    what files were affected.
    """

    success: bool = Field(..., description="Whether the patch was applied successfully")
    status: PatchStatus = Field(..., description="Status of the patch application")
    files_changed: list[str] = Field(
        default_factory=list, description="List of files modified by the patch"
    )
    error: str | None = Field(None, description="Error message if application failed")
    diff_hash: str | None = Field(None, description="Hash of the applied diff")

    @classmethod
    def applied(cls, files_changed: list[str], diff_hash: str) -> "PatchResult":
        """Create a successful patch result."""
        return cls(
            success=True,
            status=PatchStatus.APPLIED,
            files_changed=files_changed,
            diff_hash=diff_hash,
        )

    @classmethod
    def failed(cls, error: str, status: PatchStatus = PatchStatus.FAILED) -> "PatchResult":
        """Create a failed patch result."""
        return cls(
            success=False,
            status=status,
            error=error,
        )
