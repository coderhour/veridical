"""Exception hierarchy for Veridical.

All custom exceptions inherit from VeridicalError, providing a consistent
base for error handling throughout the application.
"""


class VeridicalError(Exception):
    """Base exception for all Veridical errors.

    All custom exceptions in Veridical should inherit from this class
    to enable catching all Veridical-specific errors with a single handler.
    """

    def __init__(self, message: str, *, details: str | None = None) -> None:
        """Initialize the error.

        Args:
            message: Human-readable error description.
            details: Optional additional context about the error.
        """
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class ConfigurationError(VeridicalError):
    """Invalid or missing configuration.

    Raised when configuration loading fails, required values are missing,
    or configuration validation fails.
    """

    def __init__(
        self, message: str, *, field: str | None = None, details: str | None = None
    ) -> None:
        """Initialize the configuration error.

        Args:
            message: Human-readable error description.
            field: Optional name of the configuration field that caused the error.
            details: Optional additional context about the error.
        """
        super().__init__(message, details=details)
        self.field = field


class APIError(VeridicalError):
    """Jules API communication error.

    Raised when API requests fail, return unexpected responses,
    or encounter network issues.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
        details: str | None = None,
    ) -> None:
        """Initialize the API error.

        Args:
            message: Human-readable error description.
            status_code: Optional HTTP status code from the response.
            response_body: Optional response body content.
            details: Optional additional context about the error.
        """
        super().__init__(message, details=details)
        self.status_code = status_code
        self.response_body = response_body


class RateLimitError(APIError):
    """API rate limit exceeded.

    Raised when the Jules API returns a 429 Too Many Requests response.
    Includes retry information when available.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        retry_after: float | None = None,
        details: str | None = None,
    ) -> None:
        """Initialize the rate limit error.

        Args:
            message: Human-readable error description.
            retry_after: Optional seconds to wait before retrying.
            details: Optional additional context about the error.
        """
        super().__init__(message, status_code=429, details=details)
        self.retry_after = retry_after


class AuthenticationError(APIError):
    """Authentication failed.

    Raised when API authentication fails due to invalid or missing credentials.
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        *,
        details: str | None = None,
    ) -> None:
        """Initialize the authentication error.

        Args:
            message: Human-readable error description.
            details: Optional additional context about the error.
        """
        super().__init__(message, status_code=401, details=details)


class SynchronizationError(VeridicalError):
    """Git or patch operation failed.

    Raised when git operations fail, patches cannot be applied,
    or branch management encounters issues.
    """

    def __init__(
        self,
        message: str,
        *,
        operation: str | None = None,
        details: str | None = None,
    ) -> None:
        """Initialize the synchronization error.

        Args:
            message: Human-readable error description.
            operation: Optional name of the git operation that failed.
            details: Optional additional context about the error.
        """
        super().__init__(message, details=details)
        self.operation = operation


class VerificationError(VeridicalError):
    """Quality gate verification failed.

    This is NOT a system error - it indicates that code failed to meet
    quality standards. The error includes details about which gates failed.
    """

    def __init__(
        self,
        message: str,
        *,
        failed_gates: list[str] | None = None,
        details: str | None = None,
    ) -> None:
        """Initialize the verification error.

        Args:
            message: Human-readable error description.
            failed_gates: Optional list of quality gate names that failed.
            details: Optional additional context about the error.
        """
        super().__init__(message, details=details)
        self.failed_gates = failed_gates or []


class CircuitOpenError(VeridicalError):
    """Circuit breaker tripped, aborting the loop.

    Raised when the circuit breaker detects a stuck loop condition,
    such as no progress after multiple iterations or repeated errors.
    """

    def __init__(
        self,
        message: str,
        *,
        reason: str | None = None,
        iterations: int | None = None,
        details: str | None = None,
    ) -> None:
        """Initialize the circuit open error.

        Args:
            message: Human-readable error description.
            reason: Optional reason why the circuit breaker tripped.
            iterations: Optional number of iterations completed before tripping.
            details: Optional additional context about the error.
        """
        super().__init__(message, details=details)
        self.reason = reason
        self.iterations = iterations


class TimeoutError(VeridicalError):
    """Operation timed out.

    Raised when an operation exceeds the configured timeout duration.
    """

    def __init__(
        self,
        message: str = "Operation timed out",
        *,
        timeout_seconds: float | None = None,
        details: str | None = None,
    ) -> None:
        """Initialize the timeout error.

        Args:
            message: Human-readable error description.
            timeout_seconds: Optional timeout duration in seconds.
            details: Optional additional context about the error.
        """
        super().__init__(message, details=details)
        self.timeout_seconds = timeout_seconds
