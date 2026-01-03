"""Backoff strategies for polling."""

import random
from abc import ABC, abstractmethod


class BackoffStrategy(ABC):
    """Abstract base class for backoff strategies."""

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """Get the delay for a given attempt number.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds before the next attempt
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset the backoff state."""
        ...


class ExponentialBackoff(BackoffStrategy):
    """Exponential backoff with optional jitter.

    Delay grows exponentially: base_interval * (2 ^ attempt)
    Jitter adds random variation to prevent thundering herd.
    """

    def __init__(
        self,
        base_interval: float = 30.0,
        max_interval: float = 300.0,
        jitter_factor: float = 0.1,
    ) -> None:
        """Initialize exponential backoff.

        Args:
            base_interval: Initial interval in seconds
            max_interval: Maximum interval cap in seconds
            jitter_factor: Random jitter as fraction of interval (0.0-1.0)
        """
        self.base_interval = base_interval
        self.max_interval = max_interval
        self.jitter_factor = jitter_factor
        self._attempt = 0

    def get_delay(self, attempt: int | None = None) -> float:
        """Get the delay for the next attempt.

        Args:
            attempt: Optional explicit attempt number. If None, uses internal counter.

        Returns:
            Delay in seconds with jitter applied
        """
        if attempt is None:
            attempt = self._attempt
            self._attempt += 1

        # Calculate base delay with exponential growth
        delay = self.base_interval * (2**attempt)

        # Cap at maximum
        delay = min(delay, self.max_interval)

        # Apply jitter
        if self.jitter_factor > 0:
            jitter_range = delay * self.jitter_factor
            delay += random.uniform(-jitter_range, jitter_range)

        return float(max(0, delay))

    def reset(self) -> None:
        """Reset the attempt counter."""
        self._attempt = 0


class ConstantBackoff(BackoffStrategy):
    """Constant backoff - same delay every time."""

    def __init__(self, interval: float = 30.0) -> None:
        """Initialize constant backoff.

        Args:
            interval: Interval in seconds between attempts
        """
        self.interval = interval

    def get_delay(self, _attempt: int = 0) -> float:
        """Get the constant delay.

        Args:
            attempt: Ignored for constant backoff

        Returns:
            Constant interval in seconds
        """
        return self.interval

    def reset(self) -> None:
        """Reset (no-op for constant backoff)."""
        pass
