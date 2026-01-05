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
        """Test poller initialization with default constant backoff."""
        # Default is now constant as per OpenSpec tasks
        poller = Poller(config=mock_config, api_client=mock_jules_client)
        assert isinstance(poller.backoff, ConstantBackoff)
        assert poller.backoff.interval == 30.0

    def test_poller_initialization_exponential(
        self, mock_config: VeridicalConfig, mock_jules_client: Mock
    ) -> None:
        """Test poller initialization with exponential backoff strategy."""
        mock_config.jules.backoff_strategy = "exponential"
        poller = Poller(config=mock_config, api_client=mock_jules_client)
        assert isinstance(poller.backoff, ExponentialBackoff)

    def test_poller_initialization_constant_custom_interval(
        self, mock_config: VeridicalConfig, mock_jules_client: Mock
    ) -> None:
        """Test poller initialization with constant backoff and custom interval."""
        mock_config.jules.backoff_strategy = "constant"
        mock_config.jules.poll_interval = 5.0
        poller = Poller(config=mock_config, api_client=mock_jules_client)
        assert isinstance(poller.backoff, ConstantBackoff)
        assert poller.backoff.interval == 5.0

    def test_poller_initialization_custom_strategy(
        self, mock_config: VeridicalConfig, mock_jules_client: Mock
    ) -> None:
        """Test poller initialization with a custom backoff strategy object."""

        class CustomBackoff(BackoffStrategy):
            def get_delay(self, _attempt: int) -> float:
                return 1.23

            def reset(self) -> None:
                pass

        custom_strategy = CustomBackoff()
        poller = Poller(
            config=mock_config,
            api_client=mock_jules_client,
            backoff_strategy=custom_strategy,
        )
        assert poller.backoff is custom_strategy
        assert poller.backoff.get_delay(1) == 1.23

    def test_constant_backoff_delays(
        self, mock_config: VeridicalConfig, mock_jules_client: Mock
    ) -> None:
        """Verify delays are consistent across poll attempts for constant strategy."""
        mock_config.jules.backoff_strategy = "constant"
        mock_config.jules.poll_interval = 10.0
        poller = Poller(config=mock_config, api_client=mock_jules_client)

        assert poller.backoff.get_delay(0) == 10.0
        assert poller.backoff.get_delay(1) == 10.0
        assert poller.backoff.get_delay(5) == 10.0

    def test_exponential_backoff_delays(
        self, mock_config: VeridicalConfig, mock_jules_client: Mock
    ) -> None:
        """Verify delays increase exponentially for exponential strategy."""
        mock_config.jules.backoff_strategy = "exponential"
        # Use a config where we know the exact values (no jitter)
        mock_config.jules.backoff = ExponentialBackoffConfig(
            base_interval=1.0, max_interval=100.0, jitter_factor=0.0
        )
        poller = Poller(config=mock_config, api_client=mock_jules_client)

        # 1.0 * 2^0 = 1.0
        assert poller.backoff.get_delay(0) == 1.0
        # 1.0 * 2^1 = 2.0
        assert poller.backoff.get_delay(1) == 2.0
        # 1.0 * 2^2 = 4.0
        assert poller.backoff.get_delay(2) == 4.0
        # 1.0 * 2^3 = 8.0
        assert poller.backoff.get_delay(3) == 8.0
