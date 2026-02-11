"""Unit tests for PromptOptimizer."""

from datetime import datetime

import pytest

from veridical.learning.models import (
    ErrorCategory,
    GateFailureFrequency,
    LearnedRule,
    PatternReport,
)
from veridical.learning.optimizer import PromptOptimizer


@pytest.fixture
def optimizer() -> PromptOptimizer:
    return PromptOptimizer()


@pytest.fixture
def sample_report() -> PatternReport:
    return PatternReport(
        sufficient_data=True,
        total_runs_analyzed=10,
        gate_failure_frequencies=[
            GateFailureFrequency(
                gate_name="pytest",
                failure_count=7,
                total_runs=10,
                failure_rate=0.7,
                first_iteration_failure_rate=0.8,
            ),
            GateFailureFrequency(
                gate_name="ruff",
                failure_count=2,
                total_runs=10,
                failure_rate=0.2,
                first_iteration_failure_rate=0.1,
            ),
        ],
        error_categories=[
            ErrorCategory(
                category="import errors",
                frequency=5,
                example_excerpts=["ImportError: No module named 'foo'"],
            ),
            ErrorCategory(
                category="other",
                frequency=1,
                example_excerpts=["some error"],
            ),
        ],
    )


class TestPromptOptimizer:
    def test_generate_rules_from_report(
        self, optimizer: PromptOptimizer, sample_report: PatternReport
    ) -> None:
        rules = optimizer.generate_rules(sample_report)
        assert len(rules) > 0
        assert all(isinstance(r, LearnedRule) for r in rules)

    def test_no_rules_from_insufficient_data(self, optimizer: PromptOptimizer) -> None:
        report = PatternReport(sufficient_data=False, message="Not enough data")
        rules = optimizer.generate_rules(report)
        assert rules == []

    def test_gate_failure_generates_rule(
        self, optimizer: PromptOptimizer, sample_report: PatternReport
    ) -> None:
        rules = optimizer.generate_rules(sample_report)
        triggers = [r.trigger_pattern for r in rules]
        assert "gate:pytest" in triggers

    def test_low_failure_rate_skipped(self, optimizer: PromptOptimizer) -> None:
        report = PatternReport(
            sufficient_data=True,
            total_runs_analyzed=10,
            gate_failure_frequencies=[
                GateFailureFrequency(
                    gate_name="mypy",
                    failure_count=1,
                    total_runs=10,
                    failure_rate=0.1,
                    first_iteration_failure_rate=0.1,
                ),
            ],
        )
        rules = optimizer.generate_rules(report)
        triggers = [r.trigger_pattern for r in rules]
        assert "gate:mypy" not in triggers

    def test_error_category_generates_rule(
        self, optimizer: PromptOptimizer, sample_report: PatternReport
    ) -> None:
        rules = optimizer.generate_rules(sample_report)
        triggers = [r.trigger_pattern for r in rules]
        assert "error:import errors" in triggers

    def test_deduplication_updates_existing(
        self, optimizer: PromptOptimizer, sample_report: PatternReport
    ) -> None:
        existing = [
            LearnedRule(
                id="existing-1",
                trigger_pattern="gate:pytest",
                rule_text="Old rule text",
                confidence_score=0.5,
                created_at=datetime(2025, 1, 1),
            ),
        ]
        rules = optimizer.generate_rules(sample_report, existing_rules=existing)

        pytest_rules = [r for r in rules if r.trigger_pattern == "gate:pytest"]
        assert len(pytest_rules) == 1
        assert pytest_rules[0].id == "existing-1"
        assert pytest_rules[0].confidence_score != 0.5  # Updated

    def test_rule_format(self, optimizer: PromptOptimizer, sample_report: PatternReport) -> None:
        rules = optimizer.generate_rules(sample_report)
        for rule in rules:
            assert rule.id
            assert rule.trigger_pattern
            assert rule.rule_text
            assert 0.0 <= rule.confidence_score <= 1.0
            assert isinstance(rule.created_at, datetime)

    def test_low_frequency_error_skipped(self, optimizer: PromptOptimizer) -> None:
        report = PatternReport(
            sufficient_data=True,
            total_runs_analyzed=10,
            error_categories=[
                ErrorCategory(category="rare error", frequency=1, example_excerpts=[]),
            ],
        )
        rules = optimizer.generate_rules(report)
        triggers = [r.trigger_pattern for r in rules]
        assert "error:rare error" not in triggers
