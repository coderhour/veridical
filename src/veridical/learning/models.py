"""Data models for the learning module."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GateFailureFrequency(BaseModel):
    """Frequency of a specific gate failure."""

    gate_name: str
    failure_count: int
    total_runs: int
    failure_rate: float = Field(ge=0.0, le=1.0)
    first_iteration_failure_rate: float = Field(
        ge=0.0, le=1.0, description="Rate of failure on first iteration specifically"
    )


class StagnationPattern(BaseModel):
    """A detected stagnation pattern across runs."""

    diff_hash: str
    occurrence_count: int
    affected_task_descriptions: list[str]


class ErrorCategory(BaseModel):
    """A cluster of similar errors."""

    category: str
    frequency: int
    example_excerpts: list[str] = Field(default_factory=list, max_length=5)


class PatternReport(BaseModel):
    """Report from pattern analysis of work log history."""

    sufficient_data: bool = True
    message: str | None = None
    total_runs_analyzed: int = 0
    gate_failure_frequencies: list[GateFailureFrequency] = Field(default_factory=list)
    stagnation_patterns: list[StagnationPattern] = Field(default_factory=list)
    error_categories: list[ErrorCategory] = Field(default_factory=list)
    average_iterations_per_run: float = 0.0


class LearnedRule(BaseModel):
    """A learned prompt improvement rule."""

    id: str
    trigger_pattern: str
    rule_text: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.now)
    applied_count: int = 0
    success_rate: float = Field(ge=0.0, le=1.0, default=0.0)


class SimilarTask(BaseModel):
    """A historically similar task."""

    task_description: str
    iterations_taken: int
    succeeded: bool
    similarity_score: float = Field(ge=0.0, le=1.0)


class DifficultyEstimate(BaseModel):
    """Prediction of task difficulty based on historical data."""

    predicted_iterations: int
    confidence: Literal["low", "medium", "high"]
    similar_tasks: list[SimilarTask] = Field(default_factory=list)
