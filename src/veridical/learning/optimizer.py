"""Prompt optimizer that generates improvement rules from failure patterns."""

import logging
import uuid
from datetime import datetime

from veridical.learning.models import (
    ErrorCategory,
    GateFailureFrequency,
    LearnedRule,
    PatternReport,
)

logger = logging.getLogger(__name__)

# Mapping of error categories to actionable rule texts
_CATEGORY_RULES: dict[str, str] = {
    "import errors": "Always verify import statements are correct before submitting code",
    "type errors": "Check type annotations and ensure function signatures match expected types",
    "syntax errors": "Validate syntax by running the code through a linter before submitting",
    "test failures": "Run the full test suite locally and fix all failing tests before submitting",
    "lint errors": "Run the project linter (e.g., ruff check) and fix all violations before submitting",
    "name errors": "Verify all variable and function names are defined before use",
    "attribute errors": "Check that objects have the expected attributes before accessing them",
    "value errors": "Validate input values and handle edge cases for type conversions",
    "timeout errors": "Ensure long-running operations have appropriate timeouts and error handling",
}

# Mapping of gate names to actionable rule texts
_GATE_RULES: dict[str, str] = {
    "pytest": "Ensure all tests pass before submitting changes",
    "ruff": "Run ruff check and fix all linting issues before submitting",
    "mypy": "Run mypy and resolve all type checking errors before submitting",
    "task_completion": "Verify all task checklist items are marked complete before submitting",
}

# Threshold for generating a rule from a pattern
_MIN_FAILURE_RATE = 0.3
_MIN_FREQUENCY = 2


class PromptOptimizer:
    """Generates prompt improvement rules from failure patterns."""

    def generate_rules(
        self,
        pattern_report: PatternReport,
        existing_rules: list[LearnedRule] | None = None,
    ) -> list[LearnedRule]:
        """Generate prompt improvement rules from a pattern report.

        Args:
            pattern_report: The pattern analysis report.
            existing_rules: Optional list of existing rules for deduplication.

        Returns:
            List of new or updated LearnedRule objects.
        """
        if not pattern_report.sufficient_data:
            return []

        existing = existing_rules or []
        existing_by_trigger: dict[str, LearnedRule] = {r.trigger_pattern: r for r in existing}

        rules: list[LearnedRule] = []

        # Generate rules from gate failure frequencies
        for freq in pattern_report.gate_failure_frequencies:
            rule = self._rule_from_gate_failure(freq, existing_by_trigger)
            if rule:
                rules.append(rule)

        # Generate rules from error categories
        for cat in pattern_report.error_categories:
            rule = self._rule_from_error_category(cat, existing_by_trigger)
            if rule:
                rules.append(rule)

        return rules

    def _rule_from_gate_failure(
        self,
        freq: GateFailureFrequency,
        existing: dict[str, LearnedRule],
    ) -> LearnedRule | None:
        """Generate a rule from a gate failure frequency."""
        if freq.failure_rate < _MIN_FAILURE_RATE:
            return None
        if freq.failure_count < _MIN_FREQUENCY:
            return None

        trigger = f"gate:{freq.gate_name}"
        rule_text = _GATE_RULES.get(
            freq.gate_name,
            f"Gate '{freq.gate_name}' fails frequently ({freq.failure_rate:.0%}). "
            f"Review its requirements before submitting.",
        )

        if trigger in existing:
            # Update confidence of existing rule
            existing_rule = existing[trigger]
            new_confidence = min(1.0, (existing_rule.confidence_score + freq.failure_rate) / 2)
            return LearnedRule(
                id=existing_rule.id,
                trigger_pattern=trigger,
                rule_text=rule_text,
                confidence_score=round(new_confidence, 2),
                created_at=existing_rule.created_at,
                applied_count=existing_rule.applied_count,
                success_rate=existing_rule.success_rate,
            )

        return LearnedRule(
            id=str(uuid.uuid4())[:8],
            trigger_pattern=trigger,
            rule_text=rule_text,
            confidence_score=round(min(1.0, freq.failure_rate), 2),
            created_at=datetime.now(),
        )

    def _rule_from_error_category(
        self,
        cat: ErrorCategory,
        existing: dict[str, LearnedRule],
    ) -> LearnedRule | None:
        """Generate a rule from an error category."""
        if cat.frequency < _MIN_FREQUENCY:
            return None

        trigger = f"error:{cat.category}"
        rule_text = _CATEGORY_RULES.get(
            cat.category,
            f"Error category '{cat.category}' occurs frequently ({cat.frequency} times). "
            f"Pay extra attention to avoid these errors.",
        )

        if trigger in existing:
            existing_rule = existing[trigger]
            # Boost confidence based on continued occurrence
            new_confidence = min(1.0, existing_rule.confidence_score + 0.1)
            return LearnedRule(
                id=existing_rule.id,
                trigger_pattern=trigger,
                rule_text=rule_text,
                confidence_score=round(new_confidence, 2),
                created_at=existing_rule.created_at,
                applied_count=existing_rule.applied_count,
                success_rate=existing_rule.success_rate,
            )

        # Confidence based on frequency relative to a baseline
        confidence = min(1.0, cat.frequency / 10.0)

        return LearnedRule(
            id=str(uuid.uuid4())[:8],
            trigger_pattern=trigger,
            rule_text=rule_text,
            confidence_score=round(max(0.3, confidence), 2),
            created_at=datetime.now(),
        )
