"""Async HTTP client for the Jules API."""

import asyncio
from types import TracebackType
from typing import Any

import httpx

from veridical.api.exceptions import APIError, AuthenticationError, RateLimitError
from veridical.api.models import (
    ActivityEntry,
    ApprovalRequest,
    CreateSessionRequest,
    SendMessageRequest,
    SessionResponse,
)


class JulesClient:
    """Async HTTP client for interacting with the Jules API.

    Usage:
        async with JulesClient(api_key="...") as client:
            session = await client.create_session(request)
            status = await client.get_session(session.session_id)
    """

    DEFAULT_BASE_URL = "https://jules.googleapis.com/v1alpha"
    DEFAULT_TIMEOUT = 30.0

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize the Jules API client.

        Args:
            api_key: API key for authentication.
            base_url: Base URL for the Jules API.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts.
            retry_delay: Base delay between retries in seconds.
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: httpx.AsyncClient | None = None

    async def _log_request(self, request: httpx.Request) -> None:
        print(f"DEBUG REQ: {request.method} {request.url}")
        for name, value in request.headers.items():
            if name.lower() == "x-goog-api-key":
                print(f"DEBUG REQ Header: {name}: {'*' * len(value)}")
            else:
                print(f"DEBUG REQ Header: {name}: {value}")
        if request.content:
            print(f"DEBUG REQ Body: {request.content.decode()}")

    async def __aenter__(self) -> "JulesClient":
        """Enter async context manager."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "X-Goog-Api-Key": self.api_key,
                "Content-Type": "application/json",
            },
            event_hooks={"request": [self._log_request]},
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, raising if not initialized."""
        if self._client is None:
            raise RuntimeError(
                "JulesClient must be used as an async context manager. "
                "Use 'async with JulesClient(...) as client:'"
            )
        return self._client

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (relative to base_url)
            **kwargs: Additional arguments to pass to httpx

        Returns:
            HTTP response

        Raises:
            APIError: If request fails after all retries
            RateLimitError: If rate limited
            AuthenticationError: If authentication fails
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                # Debug logging
                full_url = str(self.client.base_url.join(path))
                print(f"DEBUG: {method} {full_url}")
                if "json" in kwargs:
                    print(f"DEBUG: Payload: {kwargs['json']}")

                response = await self.client.request(method, path, **kwargs)

                # Handle specific error codes
                if response.status_code == 401:
                    raise AuthenticationError(
                        "Authentication failed",
                        details="Invalid or expired API key",
                    )

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise RateLimitError(
                        "Rate limit exceeded",
                        retry_after=float(retry_after) if retry_after else None,
                    )

                # Raise for other error status codes
                if response.status_code >= 400:
                    print(f"DEBUG: Response body: {response.text}")
                    raise APIError(
                        f"API request failed: {response.status_code}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

                # Debug log successful response
                if response.status_code < 300:
                    print(f"DEBUG: Response body: {response.text}")

                return response

            except (RateLimitError, AuthenticationError):
                # Don't retry these errors
                raise

            except APIError as e:
                # Only retry 5xx errors
                if e.status_code and e.status_code < 500:
                    raise
                last_error = e

            except httpx.RequestError as e:
                # Network errors are retryable
                last_error = APIError(
                    f"Network error: {e}",
                    details=str(e),
                )

            # Wait before retry (exponential backoff)
            if attempt < self.max_retries:
                delay = self.retry_delay * (2**attempt)
                await asyncio.sleep(delay)

        # All retries exhausted
        raise last_error or APIError("Request failed after retries")

    async def create_session(self, request: CreateSessionRequest) -> SessionResponse:
        """Create a new Jules session.

        Args:
            request: Session creation request

        Returns:
            Created session information
        """
        response = await self._request_with_retry(
            "POST",
            "/sessions",
            json=request.model_dump_api(),
        )
        return SessionResponse.model_validate(response.json())

    async def get_session(self, session_id: str) -> SessionResponse:
        """Get the current status of a session.

        Args:
            session_id: ID of the session to retrieve

        Returns:
            Current session information
        """
        response = await self._request_with_retry(
            "GET",
            f"/sessions/{session_id}",
        )
        return SessionResponse.model_validate(response.json())

    async def approve_plan(self, session_id: str) -> None:
        """Approve a session's plan.

        Args:
            session_id: ID of the session to approve
        """
        request = ApprovalRequest()
        await self._request_with_retry(
            "POST",
            f"/sessions/{session_id}:approvePlan",
            json=request.model_dump(),
        )

    async def send_message(self, session_id: str, message: str) -> None:
        """Send a message to a session.

        Args:
            session_id: ID of the session
            message: Message to send
        """
        request = SendMessageRequest(message=message)
        await self._request_with_retry(
            "POST",
            f"/sessions/{session_id}:sendMessage",
            json=request.model_dump(),
        )

    async def get_activities(self, session_id: str) -> list[ActivityEntry]:
        """Get activity log for a session.

        Args:
            session_id: ID of the session

        Returns:
            List of activity entries
        """
        response = await self._request_with_retry(
            "GET",
            f"/sessions/{session_id}/activities",
        )
        data = response.json()
        activities = data.get("activities", [])
        return [ActivityEntry.model_validate(a) for a in activities]

    async def download_patch(self, session_id: str) -> str:
        """Download patch for a session by extracting it from activities.

        Args:
            session_id: ID of the session

        Returns:
            Unified diff content
        """
        activities = await self.get_activities(session_id)

        # Iterate in reverse to find the most recent patch
        for activity in reversed(activities):
            for artifact in activity.artifacts:
                if artifact.change_set and artifact.change_set.git_patch:
                    patch = artifact.change_set.git_patch.unidiff_patch
                    if patch:
                        return patch

        return ""
