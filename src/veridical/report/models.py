"""Data models for run reports."""

from datetime import datetime

from pydantic import BaseModel, Field


class CostSummary(BaseModel):
    """Aggregate cost metrics for a run."""

    total_api_calls: int = 0
    total_estimated_tokens: int = 0
    total_vm_time_seconds: float = 0.0


class IterationDetail(BaseModel):
    """Per-iteration breakdown for a run report."""

    iteration: int
    timestamp: datetime
    duration_seconds: float | None = None
    gates_executed: list[str] = Field(default_factory=list)
    gates_failed: list[str] = Field(default_factory=list)
    verification_passed: bool | None = None
    feedback_excerpt: str | None = None
    api_calls_count: int | None = None
    estimated_tokens: int | None = None
    vm_time_seconds: float | None = None


class PatternInsight(BaseModel):
    """A detected pattern from run analysis."""

    category: str  # "frequent_failure", "first_iter_failure", "stagnation"
    description: str
    gate_name: str | None = None
    iterations_affected: list[int] = Field(default_factory=list)


class RunSummary(BaseModel):
    """Structured summary of a completed run."""

    run_date: str
    session_id: str
    task_description: str
    outcome: str  # "success" or "failure"
    total_iterations: int
    total_duration_seconds: float | None = None
    started_at: datetime
    completed_at: datetime
    most_failed_gate: str | None = None
    cost: CostSummary = Field(default_factory=CostSummary)
    iterations: list[IterationDetail] = Field(default_factory=list)
    patterns: list[PatternInsight] = Field(default_factory=list)
