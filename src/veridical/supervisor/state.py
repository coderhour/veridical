"""Supervisor state machine definitions."""

from enum import Enum, auto


class SupervisorState(Enum):
    """States of the supervisor control loop.

    The supervisor transitions through these states during execution:
    IDLE -> DISPATCHING -> POLLING -> SYNCING -> VERIFYING -> SUCCESS/FAILED
    """

    IDLE = auto()
    DISPATCHING = auto()
    POLLING = auto()
    SYNCING = auto()
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
            SupervisorState.VERIFYING,
        )


# Valid state transitions
VALID_TRANSITIONS: dict[SupervisorState, set[SupervisorState]] = {
    SupervisorState.IDLE: {SupervisorState.DISPATCHING, SupervisorState.FAILED},
    SupervisorState.DISPATCHING: {SupervisorState.POLLING, SupervisorState.FAILED},
    SupervisorState.POLLING: {SupervisorState.SYNCING, SupervisorState.FAILED},
    SupervisorState.SYNCING: {SupervisorState.VERIFYING, SupervisorState.FAILED},
    SupervisorState.VERIFYING: {
        SupervisorState.SUCCESS,
        SupervisorState.DISPATCHING,  # Loop back on failure
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
