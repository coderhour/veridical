"""Unit test specific fixtures."""

import pytest

from veridical.config.schema import (
    GitConfig,
    JulesConfig,
    QualityGate,
    SupervisorConfig,
    VeridicalConfig,
    VerifierConfig,
)


@pytest.fixture
def default_config() -> VeridicalConfig:
    """Provide a default configuration for unit tests."""
    return VeridicalConfig(
        jules=JulesConfig(),
        supervisor=SupervisorConfig(),
        verifier=VerifierConfig(
            quality_gates=[
                QualityGate(name="pytest", command="pytest"),
                QualityGate(name="ruff", command="ruff check src/"),
            ]
        ),
        git=GitConfig(),
    )
