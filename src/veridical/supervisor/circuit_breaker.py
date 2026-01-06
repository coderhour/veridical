"""Circuit breaker implementation for preventing runaway loops."""

from veridical.exceptions import CircuitOpenError


class CircuitBreaker:
    """Circuit breaker to prevent runaway loops.

    Monitors loop iterations for signs of stagnation or repeated failures
    and trips (opens) the circuit when thresholds are exceeded.
    """

    def __init__(
        self,
        max_iterations: int = 10,
        max_consecutive_failures: int = 3,
        stagnation_threshold: int = 3,
    ) -> None:
        """Initialize the circuit breaker.

        Args:
            max_iterations: Maximum total iterations before circuit opens.
            max_consecutive_failures: Maximum consecutive failures allowed.
            stagnation_threshold: Number of identical diffs before stagnation.
        """
        self.max_iterations = max_iterations
        self.max_consecutive_failures = max_consecutive_failures
        self.stagnation_threshold = stagnation_threshold

        self._iteration_count = 0
        self._consecutive_failures = 0
        self._diff_hashes: list[str] = []
        self._is_open = False
        self._open_reason: str | None = None

    @property
    def is_open(self) -> bool:
        """Check if the circuit is open (tripped)."""
        return self._is_open

    @property
    def open_reason(self) -> str | None:
        """Get the reason the circuit was opened."""
        return self._open_reason

    @property
    def iteration_count(self) -> int:
        """Get the current iteration count."""
        return self._iteration_count

    def record_iteration(self) -> None:
        """Record a new iteration starting."""
        self._iteration_count += 1
        if self._iteration_count > self.max_iterations:
            self._trip("Maximum iterations exceeded")

    def record_success(self) -> None:
        """Record a successful iteration."""
        self._consecutive_failures = 0

    def record_failure(self) -> None:
        """Record a failed iteration."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.max_consecutive_failures:
            self._trip("Maximum consecutive failures reached")

    def record_diff_hash(self, diff_hash: str) -> None:
        """Record a diff hash for stagnation detection.

        Args:
            diff_hash: Hash of the current diff
        """
        self._diff_hashes.append(diff_hash)

        # Check for stagnation (same diff repeated)
        if len(self._diff_hashes) >= self.stagnation_threshold:
            recent = self._diff_hashes[-self.stagnation_threshold :]
            if len(set(recent)) == 1:
                self._trip("Stagnation detected - identical diffs")

    def _trip(self, reason: str) -> None:
        """Trip (open) the circuit.

        Args:
            reason: Why the circuit was tripped
        """
        self._is_open = True
        self._open_reason = reason

    def check(self) -> None:
        """Check if the circuit is open and raise if so.

        Raises:
            CircuitOpenError: If the circuit is open
        """
        if self._is_open:
            raise CircuitOpenError(
                "Circuit breaker tripped",
                reason=self._open_reason,
                iterations=self._iteration_count,
            )

    def reset(self) -> None:
        """Reset the circuit breaker to initial state."""
        self._iteration_count = 0
        self._consecutive_failures = 0
        self._diff_hashes.clear()
        self._is_open = False
        self._open_reason = None
