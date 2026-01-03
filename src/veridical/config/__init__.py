"""Configuration module - settings loading and validation."""

from veridical.config.loader import load_config
from veridical.config.schema import (
    GitConfig,
    JulesConfig,
    QualityGate,
    SupervisorConfig,
    VeridicalConfig,
    VerifierConfig,
)

__all__ = [
    "GitConfig",
    "JulesConfig",
    "QualityGate",
    "SupervisorConfig",
    "VeridicalConfig",
    "VerifierConfig",
    "load_config",
]
