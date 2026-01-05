"""Session status monitoring and polling."""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from veridical.api.models import ActivityEntry, SessionState
from veridical.exceptions import TimeoutError
from veridical.poller.backoff import (
    BackoffStrategy,
    ConstantBackoff,
    create_backoff_strategy,
)

if TYPE_CHECKING:
    from veridical.api.client import JulesClient
    from veridical.cli.progress import ProgressReporter
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
        progress: "ProgressReporter | None" = None,
    ) -> None:
        """Initialize the poller.

        Args:
            config: Veridical configuration
            api_client: Jules API client
            backoff_strategy: Optional custom backoff strategy
            progress: Optional progress reporter for rich display
        """
        self.config = config
        self.api_client = api_client
        self.progress = progress
        self.seen_activity_ids: set[str] = set()

        if backoff_strategy:
            self.backoff = backoff_strategy
        elif config.jules.backoff_strategy == "constant":
            self.backoff = ConstantBackoff(interval=config.jules.poll_interval)
        else:
            # For exponential, use the detailed config if available,
            # or default to ExponentialBackoff if not.
            # (config.jules.backoff will be an ExponentialBackoffConfig
            # if that's what's in the schema default or loaded from yaml)
            self.backoff = create_backoff_strategy(config.jules.backoff)

    def _format_activity(self, entry: ActivityEntry) -> str | None:
        """Format an activity entry into a human-readable string."""
        if entry.type == "USER_MESSAGED":
            return f"💬 User: {entry.message}"
        if entry.type == "AGENT_MESSAGED":
            return f"🤖 Jules: {entry.message}"
        if entry.type == "PLAN_GENERATED":
            return "📝 Plan generated"
        if entry.type == "PROGRESS_UPDATED" and entry.message:
            return f"🔄 {entry.message}"
        if entry.type == "SESSION_COMPLETED":
            return "✅ Session completed"
        if entry.type == "SESSION_FAILED":
            return f"❌ Session failed: {entry.message}"
        return None  # Ignore other types for now

    async def stream_activities(self, session_id: str) -> None:
        """Stream new activities to the progress reporter."""
        if not self.progress or not self.progress.verbose:
            return

        try:
            activities = await self.api_client.get_activities(session_id)
            new_activities = [
                act for act in activities if act.id and act.id not in self.seen_activity_ids
            ]

            # Sort by create time just in case the API doesn't guarantee order
            new_activities.sort(key=lambda a: a.create_time or datetime.min)

            for activity in new_activities:
                if activity.id:
                    self.seen_activity_ids.add(activity.id)
                    formatted = self._format_activity(activity)
                    if formatted:
                        self.progress.stream_activity(formatted)

            # Also update the last activity summary
            if activities:
                last_activity = activities[-1]
                self.progress.set_last_activity(
                    last_activity.message or last_activity.type or "Polling..."
                )

        except Exception as e:
            logger.warning(f"Failed to fetch or stream activities: {e}")

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

        if self.progress:
            self.progress.set_state("Starting session...")
            self.progress.set_iterations(0)

        logger.info(f"Polling session {session_id} for completion...")

        self.backoff.reset()
        self.seen_activity_ids.clear()

        last_state = None
        while True:
            # Check timeout
            elapsed = (datetime.now() - started_at).total_seconds()
            if elapsed > poll_timeout:
                if self.progress:
                    self.progress.set_state("[bold red]Timeout[/bold red]")
                raise TimeoutError(
                    f"Polling timed out after {poll_timeout} seconds",
                    timeout_seconds=poll_timeout,
                    details=f"Session {session_id} did not complete in time",
                )

            # Poll current status
            session = await self.api_client.get_session(session_id)
            poll_count += 1
            logger.info(f"Polling {poll_count}: Session {session_id} state: {session.state}")

            if self.progress:
                state_str = session.state.value if session.state else "Unknown"
                self.progress.set_state(f"State: [bold]{state_str}[/bold]")
                self.progress.set_iterations(poll_count)
                await self.stream_activities(session_id)

            if session.state != last_state:
                logger.info(f"Session {session_id} state: {session.state}")
                last_state = session.state

            # Check for terminal state
            if session.state in (SessionState.COMPLETED, SessionState.FAILED):
                if self.progress:
                    final_style = "green" if session.state == SessionState.COMPLETED else "red"
                    self.progress.set_state(f"[{final_style}]Finished: {session.state.value}[/]")
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
                    if self.progress:
                        self.progress.set_last_activity("Auto-approving plan...")
                    await self.api_client.approve_plan(session_id)

            elif session.state == SessionState.AWAITING_USER_FEEDBACK:
                # Send a default continuation message
                if self.progress:
                    self.progress.set_last_activity("Sending default continuation message...")
                await self.api_client.send_message(
                    session_id,
                    "Proceed with the optimal solution.",
                )

            # Wait before next poll
            delay = self.backoff.get_delay(poll_count)
            await asyncio.sleep(delay)
