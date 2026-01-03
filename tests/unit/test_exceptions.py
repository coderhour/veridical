"""Tests for the exception hierarchy."""

import pytest

from veridical.exceptions import (
    APIError,
    AuthenticationError,
    CircuitOpenError,
    ConfigurationError,
    RateLimitError,
    SynchronizationError,
    TimeoutError,
    VeridicalError,
    VerificationError,
)


@pytest.mark.unit
class TestVeridicalError:
    """Tests for the base VeridicalError class."""

    def test_basic_error(self) -> None:
        """Test basic error creation."""
        error = VeridicalError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.details is None

    def test_error_with_details(self) -> None:
        """Test error with details."""
        error = VeridicalError("Something went wrong", details="More info here")
        assert str(error) == "Something went wrong: More info here"
        assert error.details == "More info here"

    def test_inheritance(self) -> None:
        """Test that all errors inherit from VeridicalError."""
        errors = [
            ConfigurationError("test"),
            APIError("test"),
            RateLimitError(),
            AuthenticationError(),
            SynchronizationError("test"),
            VerificationError("test"),
            CircuitOpenError("test"),
            TimeoutError(),
        ]
        for error in errors:
            assert isinstance(error, VeridicalError)
            assert isinstance(error, Exception)


@pytest.mark.unit
class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_with_field(self) -> None:
        """Test error with field information."""
        error = ConfigurationError(
            "Invalid value",
            field="jules.poll_interval",
            details="Must be positive",
        )
        assert error.field == "jules.poll_interval"
        assert "Invalid value" in str(error)


@pytest.mark.unit
class TestAPIError:
    """Tests for API-related errors."""

    def test_api_error_with_status(self) -> None:
        """Test API error with status code."""
        error = APIError(
            "Request failed",
            status_code=500,
            response_body='{"error": "Internal error"}',
        )
        assert error.status_code == 500
        assert error.response_body == '{"error": "Internal error"}'

    def test_rate_limit_error(self) -> None:
        """Test rate limit error."""
        error = RateLimitError(retry_after=60.0)
        assert error.status_code == 429
        assert error.retry_after == 60.0

    def test_authentication_error(self) -> None:
        """Test authentication error."""
        error = AuthenticationError()
        assert error.status_code == 401


@pytest.mark.unit
class TestSynchronizationError:
    """Tests for SynchronizationError."""

    def test_with_operation(self) -> None:
        """Test error with operation information."""
        error = SynchronizationError(
            "Failed to apply patch",
            operation="git apply",
        )
        assert error.operation == "git apply"


@pytest.mark.unit
class TestVerificationError:
    """Tests for VerificationError."""

    def test_with_failed_gates(self) -> None:
        """Test error with failed gates list."""
        error = VerificationError(
            "Quality gates failed",
            failed_gates=["pytest", "ruff"],
        )
        assert error.failed_gates == ["pytest", "ruff"]

    def test_default_empty_gates(self) -> None:
        """Test default empty failed gates."""
        error = VerificationError("Quality gates failed")
        assert error.failed_gates == []


@pytest.mark.unit
class TestCircuitOpenError:
    """Tests for CircuitOpenError."""

    def test_with_reason_and_iterations(self) -> None:
        """Test error with reason and iteration count."""
        error = CircuitOpenError(
            "Circuit breaker tripped",
            reason="No progress detected",
            iterations=5,
        )
        assert error.reason == "No progress detected"
        assert error.iterations == 5


@pytest.mark.unit
class TestTimeoutError:
    """Tests for TimeoutError."""

    def test_with_timeout_seconds(self) -> None:
        """Test error with timeout duration."""
        error = TimeoutError(timeout_seconds=300.0)
        assert error.timeout_seconds == 300.0
        assert "timed out" in str(error).lower()
