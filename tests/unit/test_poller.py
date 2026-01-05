"""Tests for the Poller component."""
import pytest
from unittest.mock import MagicMock, AsyncMock

from veridical.poller.monitor import Poller
from veridical.poller.backoff import ConstantBackoff, ExponentialBackoff
from veridical.config.schema import VeridicalConfig, JulesConfig


@pytest.mark.unit
class TestPoller:
    """Tests for the Poller."""

    def test_constant_backoff_strategy(self):
        """Test that the Poller uses ConstantBackoff when configured."""
        config = VeridicalConfig(jules=JulesConfig(backoff_strategy="constant"))
        api_client = MagicMock()
        poller = Poller(config, api_client)
        assert isinstance(poller.backoff, ConstantBackoff)

    def test_exponential_backoff_strategy(self):
        """Test that the Poller uses ExponentialBackoff when configured."""
        config = VeridicalConfig(jules=JulesConfig(backoff_strategy="exponential"))
        api_client = MagicMock()
        poller = Poller(config, api_client)
        assert isinstance(poller.backoff, ExponentialBackoff)

    def test_default_backoff_strategy(self):
        """Test that the Poller defaults to ConstantBackoff."""
        config = VeridicalConfig()
        api_client = MagicMock()
        poller = Poller(config, api_client)
        assert isinstance(poller.backoff, ConstantBackoff)

    @pytest.mark.asyncio
    async def test_wait_for_completion(self):
        """Test the wait_for_completion method."""
        config = VeridicalConfig()
        api_client = MagicMock()
        api_client.get_session = AsyncMock()
        api_client.get_session.return_value.state = "COMPLETED"

        poller = Poller(config, api_client)
        result = await poller.wait_for_completion("session-123")

        assert result.final_state == "COMPLETED"
        api_client.get_session.assert_called_once_with("session-123")
