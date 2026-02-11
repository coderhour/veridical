"""Learning module for analyzing work log history and generating actionable insights."""

from veridical.learning.estimator import DifficultyEstimator
from veridical.learning.models import (
    DifficultyEstimate,
    ErrorCategory,
    LearnedRule,
    PatternReport,
    StagnationPattern,
)
from veridical.learning.optimizer import PromptOptimizer
from veridical.learning.patterns import PatternAnalyzer
from veridical.learning.rules import RuleManager

__all__ = [
    "DifficultyEstimate",
    "DifficultyEstimator",
    "ErrorCategory",
    "LearnedRule",
    "PatternAnalyzer",
    "PatternReport",
    "PromptOptimizer",
    "RuleManager",
    "StagnationPattern",
]
