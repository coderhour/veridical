"""Tests for the poller component."""

from unittest.mock import Mock

import pytest

from veridical.config.schema import (
    ConstantBackoffConfig,
    ExponentialBackoffConfig,
    VeridicalConfig,
)
from veridical.poller.backoff import (
    BackoffStrategy,
    ConstantBackoff,
    ExponentialBackoff,
    create_backoff_strategy,
)
from veridical.poller.monitor import Poller


@pytest.mark.unit
class TestBackoffFactory:
    """Tests for the backoff strategy factory."""

    def test_create_constant_backoff(self) -> None:
        """Test creating a constant backoff strategy."""
        config = ConstantBackoffConfig(interval=10)
        strategy = create_backoff_strategy(config)
        assert isinstance(strategy, ConstantBackoff)
        assert strategy.interval == 10

    def test_create_exponential_backoff(self) -> None:
        """Test creating an exponential backoff strategy."""
        config = ExponentialBackoffConfig(base_interval=5, max_interval=50, jitter_factor=0.2)
        strategy = create_backoff_strategy(config)
        assert isinstance(strategy, ExponentialBackoff)
        assert strategy.base_interval == 5
        assert strategy.max_interval == 50
        assert strategy.jitter_factor == 0.2


@pytest.fixture
def mock_jules_client() -> Mock:
    """Fixture for a mocked Jules API client."""
    return Mock()


@pytest.fixture
def mock_config() -> VeridicalConfig:
    """Fixture for a mock VeridicalConfig."""
    config = VeridicalConfig()
    config.jules.backoff = ExponentialBackoffConfig()
    return config


@pytest.mark.unit
class TestPoller:
    """Tests for the Poller."""

    def test_poller_initialization_default(
        self, mock_config: VeridicalConfig, mock_jules_client: Mock
    ) -> None:
        """Test poller initialization with default exponential backoff."""
        poller = Poller(config=mock_config, api_client=mock_jules_client)
        assert isinstance(poller.backoff, ExponentialBackoff)

    def test_poller_initialization_constant(
        self, mock_config: VeridicalConfig, mock_jules_client: Mock
    ) -> None:
        """Test poller initialization with constant backoff."""
        mock_config.jules.backoff = ConstantBackoffConfig(interval=5)
        poller = Poller(config=mock_config, api_client=mock_jules_client)
        assert isinstance(poller.backoff, ConstantBackoff)
        assert poller.backoff.interval == 5

    def test_poller_initialization_custom_strategy(
        self, mock_config: VeridicalConfig, mock_jules_client: Mock
    ) -> None:
        """Test poller initialization with a custom backoff strategy."""

        class CustomBackoff(BackoffStrategy):
            def get_delay(self, _attempt: int) -> float:
                return 1.0

            def reset(self) -> None:
                pass

        custom_strategy = CustomBackoff()
        poller = Poller(
            config=mock_config,
            api_client=mock_jules_client,
            backoff_strategy=custom_strategy,
        )
        assert poller.backoff is custom_strategy
