"""Supervisor state machine definitions."""

from enum import Enum, auto
from pathlib import Path

from pydantic import BaseModel


class SupervisorState(Enum):
    """States of the supervisor control loop.

    The supervisor transitions through these states during execution:
    IDLE -> DISPATCHING -> POLLING -> SYNCING -> VERIFYING -> SUCCESS/FAILED
    """

    IDLE = auto()
    DISPATCHING = auto()
    POLLING = auto()
    SYNCING = auto()
    RUNNING = auto()  # Used for local execution
    VERIFYING = auto()
    SUCCESS = auto()
    FAILED = auto()

    def is_terminal(self) -> bool:
        """Check if this is a terminal state."""
        return self in (SupervisorState.SUCCESS, SupervisorState.FAILED)

    def is_active(self) -> bool:
        """Check if this is an active processing state."""
        return self in (
            SupervisorState.DISPATCHING,
            SupervisorState.POLLING,
            SupervisorState.SYNCING,
            SupervisorState.RUNNING,
            SupervisorState.VERIFYING,
        )


# Valid state transitions
VALID_TRANSITIONS: dict[SupervisorState, set[SupervisorState]] = {
    SupervisorState.IDLE: {
        SupervisorState.DISPATCHING,
        SupervisorState.RUNNING,
        SupervisorState.FAILED,
    },
    SupervisorState.DISPATCHING: {SupervisorState.POLLING, SupervisorState.FAILED},
    SupervisorState.POLLING: {SupervisorState.SYNCING, SupervisorState.FAILED},
    SupervisorState.SYNCING: {SupervisorState.VERIFYING, SupervisorState.FAILED},
    SupervisorState.RUNNING: {SupervisorState.VERIFYING, SupervisorState.FAILED},
    SupervisorState.VERIFYING: {
        SupervisorState.SUCCESS,
        SupervisorState.DISPATCHING,  # Loop back on failure (remote)
        SupervisorState.RUNNING,  # Loop back on failure (local)
        SupervisorState.FAILED,
    },
    SupervisorState.SUCCESS: set(),  # Terminal state
    SupervisorState.FAILED: set(),  # Terminal state
}


def is_valid_transition(from_state: SupervisorState, to_state: SupervisorState) -> bool:
    """Check if a state transition is valid.

    Args:
        from_state: Current state
        to_state: Target state

    Returns:
        True if the transition is allowed
    """
    return to_state in VALID_TRANSITIONS.get(from_state, set())


class LoopState(BaseModel):
    """Persistent state of the supervisor loop."""

    task_description: str
    iteration: int
    session_id: str
    work_branch: str
    error_context: str | None = None
    started_at_timestamp: float = 0.0

    def save(self, path: Path) -> None:
        """Save state to file."""
        with path.open("w") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path) -> "LoopState":
        """Load state from file."""
        if not path.exists():
            raise FileNotFoundError(f"State file not found: {path}")
        with path.open() as f:
            return cls.model_validate_json(f.read())
