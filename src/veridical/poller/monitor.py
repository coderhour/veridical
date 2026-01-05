"""Session status monitoring and polling."""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from veridical.api.models import SessionState
from veridical.exceptions import TimeoutError
from veridical.poller.backoff import BackoffStrategy, ConstantBackoff, ExponentialBackoff

if TYPE_CHECKING:
    from veridical.api.client import JulesClient
    from veridical.config.schema import VeridicalConfig

logger = logging.getLogger(__name__)


class PollResult(BaseModel):
    """Result of a polling operation."""

    session_id: str = Field(..., description="Session ID")
    final_state: SessionState = Field(..., description="Final state when polling ended")
    started_at: datetime = Field(..., description="When polling started")
    completed_at: datetime = Field(..., description="When polling completed")
    poll_count: int = Field(..., ge=0, description="Number of poll attempts")

    @property
    def duration_seconds(self) -> float:
        """Calculate polling duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()


class Poller:
    """Monitors Jules session status with intelligent backoff.

    The Poller handles:
    1. Polling the Jules API for session status
    2. Automatic plan approval in autonomous mode
    3. Exponential backoff between poll attempts
    4. Timeout handling
    """

    def __init__(
        self,
        config: "VeridicalConfig",
        api_client: "JulesClient",
        *,
        backoff_strategy: BackoffStrategy | None = None,
    ) -> None:
        """Initialize the poller.

        Args:
            config: Veridical configuration
            api_client: Jules API client
            backoff_strategy: Optional custom backoff strategy
        """
        self.config = config
        self.api_client = api_client
        if backoff_strategy:
            self.backoff = backoff_strategy
        elif config.jules.backoff_strategy == "constant":
            self.backoff = ConstantBackoff(
                interval=config.jules.poll_interval,
            )
        else:  # exponential
            self.backoff = ExponentialBackoff(
                base_interval=config.jules.poll_interval,
            )

    async def wait_for_completion(
        self,
        session_id: str,
        *,
        timeout: float | None = None,
    ) -> PollResult:
        """Wait for a session to reach a terminal state.

        Args:
            session_id: ID of the session to monitor
            timeout: Optional timeout override in seconds

        Returns:
            Poll result with final state

        Raises:
            TimeoutError: If polling exceeds timeout
        """
        poll_timeout = timeout or self.config.jules.poll_timeout
        started_at = datetime.now()
        poll_count = 0

        logger.info(f"Polling session {session_id} for completion...")

        self.backoff.reset()

        while True:
            # Check timeout
            elapsed = (datetime.now() - started_at).total_seconds()
            if elapsed > poll_timeout:
                raise TimeoutError(
                    f"Polling timed out after {poll_timeout} seconds",
                    timeout_seconds=poll_timeout,
                    details=f"Session {session_id} did not complete in time",
                )

            # Poll current status
            session = await self.api_client.get_session(session_id)
            poll_count += 1

            logger.debug(f"Session {session_id} state: {session.state} (poll #{poll_count})")

            # Check for terminal state
            if session.state in (SessionState.COMPLETED, SessionState.FAILED):
                return PollResult(
                    session_id=session_id,
                    final_state=session.state,
                    started_at=started_at,
                    completed_at=datetime.now(),
                    poll_count=poll_count,
                )

            # Handle waiting states
            if session.state == SessionState.AWAITING_PLAN_APPROVAL:
                if self.config.jules.auto_approve_plans:
                    logger.info(f"Auto-approving plan for session {session_id}")
                    await self.api_client.approve_plan(session_id)

            elif session.state == SessionState.AWAITING_USER_FEEDBACK:
                # Send a default continuation message
                await self.api_client.send_message(
                    session_id,
                    "Proceed with the optimal solution.",
                )

            # Wait before next poll
            delay = self.backoff.get_delay(poll_count)
            await asyncio.sleep(delay)
