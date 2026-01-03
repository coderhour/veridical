"""Tests for the Jules API client."""

from datetime import datetime

import httpx
import pytest
import respx

from veridical.api.client import JulesClient
from veridical.api.exceptions import APIError, AuthenticationError, RateLimitError
from veridical.api.models import (
    AutomationMode,
    CreateSessionRequest,
    GitHubRepoContext,
    SessionResponse,
    SessionState,
    SourceContext,
)


@pytest.mark.unit
class TestAPIModels:
    """Tests for API models."""

    def test_create_session_request(self) -> None:
        """Test CreateSessionRequest model."""
        request = CreateSessionRequest(
            prompt="Fix the bug",
            source_context=SourceContext(
                source="sources/github/owner/repo",
                github_repo_context=GitHubRepoContext(starting_branch="main"),
            ),
        )
        assert request.prompt == "Fix the bug"
        assert request.require_plan_approval is False

    def test_create_session_request_dump_api(self) -> None:
        """Test API serialization with camelCase."""
        request = CreateSessionRequest(
            prompt="Fix the bug",
            source_context=SourceContext(source="sources/github/owner/repo"),
            require_plan_approval=False,
        )
        data = request.model_dump_api()
        assert "requirePlanApproval" in data
        assert "sourceContext" in data
        assert data["requirePlanApproval"] is False

    def test_session_response(self) -> None:
        """Test SessionResponse model."""
        response = SessionResponse(
            name="sessions/abc123",
            state=SessionState.RUNNING,
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        assert response.session_id == "abc123"
        assert response.state == SessionState.RUNNING


@pytest.mark.unit
class TestJulesClient:
    """Tests for JulesClient."""

    @pytest.fixture
    def api_key(self) -> str:
        """Test API key."""
        return "test-api-key"

    @pytest.mark.asyncio
    async def test_client_context_manager(self, api_key: str) -> None:
        """Test client as context manager."""
        async with JulesClient(api_key=api_key) as client:
            assert client._client is not None
        assert client._client is None

    def test_client_not_in_context(self, api_key: str) -> None:
        """Test error when client not in context."""
        client = JulesClient(api_key=api_key)
        with pytest.raises(RuntimeError, match="context manager"):
            _ = client.client

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_session(self, api_key: str) -> None:
        """Test creating a session."""
        respx.post("https://jules.googleapis.com/v1alpha/sessions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "name": "sessions/test-123",
                    "state": "PENDING",
                    "createTime": "2024-01-01T00:00:00Z",
                    "updateTime": "2024-01-01T00:00:00Z",
                },
            )
        )

        async with JulesClient(api_key=api_key) as client:
            request = CreateSessionRequest(
                prompt="Fix the bug",
                source_context=SourceContext(source="sources/github/owner/repo"),
            )
            response = await client.create_session(request)

        assert response.session_id == "test-123"
        assert response.state == SessionState.PENDING

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_session(self, api_key: str) -> None:
        """Test getting session status."""
        respx.get("https://jules.googleapis.com/v1alpha/sessions/test-123").mock(
            return_value=httpx.Response(
                200,
                json={
                    "name": "sessions/test-123",
                    "state": "COMPLETED",
                    "createTime": "2024-01-01T00:00:00Z",
                    "updateTime": "2024-01-01T00:00:01Z",
                },
            )
        )

        async with JulesClient(api_key=api_key) as client:
            response = await client.get_session("test-123")

        assert response.state == SessionState.COMPLETED

    @pytest.mark.asyncio
    @respx.mock
    async def test_approve_plan(self, api_key: str) -> None:
        """Test approving a plan."""
        respx.post("https://jules.googleapis.com/v1alpha/sessions/test-123:approvePlan").mock(
            return_value=httpx.Response(200, json={})
        )

        async with JulesClient(api_key=api_key) as client:
            await client.approve_plan("test-123")

    @pytest.mark.asyncio
    @respx.mock
    async def test_send_message(self, api_key: str) -> None:
        """Test sending a message."""
        respx.post("https://jules.googleapis.com/v1alpha/sessions/test-123:sendMessage").mock(
            return_value=httpx.Response(200, json={})
        )

        async with JulesClient(api_key=api_key) as client:
            await client.send_message("test-123", "Continue with the fix")

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_activities(self, api_key: str) -> None:
        """Test getting activities."""
        respx.get("https://jules.googleapis.com/v1alpha/sessions/test-123/activities").mock(
            return_value=httpx.Response(
                200,
                json={
                    "activities": [
                        {
                            "timestamp": "2024-01-01T00:00:00Z",
                            "type": "LOG",
                            "message": "Started processing",
                        }
                    ]
                },
            )
        )

        async with JulesClient(api_key=api_key) as client:
            activities = await client.get_activities("test-123")

        assert len(activities) == 1
        assert activities[0].type == "LOG"

    @pytest.mark.asyncio
    @respx.mock
    async def test_authentication_error(self, api_key: str) -> None:
        """Test authentication error handling."""
        respx.get("https://jules.googleapis.com/v1alpha/sessions/test-123").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )

        async with JulesClient(api_key=api_key) as client:
            with pytest.raises(AuthenticationError):
                await client.get_session("test-123")

    @pytest.mark.asyncio
    @respx.mock
    async def test_rate_limit_error(self, api_key: str) -> None:
        """Test rate limit error handling."""
        respx.get("https://jules.googleapis.com/v1alpha/sessions/test-123").mock(
            return_value=httpx.Response(
                429,
                json={"error": "Rate limited"},
                headers={"Retry-After": "60"},
            )
        )

        async with JulesClient(api_key=api_key) as client:
            with pytest.raises(RateLimitError) as exc_info:
                await client.get_session("test-123")

        assert exc_info.value.retry_after == 60.0

    @pytest.mark.asyncio
    @respx.mock
    async def test_api_error(self, api_key: str) -> None:
        """Test generic API error handling."""
        respx.get("https://jules.googleapis.com/v1alpha/sessions/test-123").mock(
            return_value=httpx.Response(400, json={"error": "Bad request"})
        )

        async with JulesClient(api_key=api_key) as client:
            with pytest.raises(APIError) as exc_info:
                await client.get_session("test-123")

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_on_server_error(self, api_key: str) -> None:
        """Test retry on 5xx errors."""
        route = respx.get("https://jules.googleapis.com/v1alpha/sessions/test-123")
        route.side_effect = [
            httpx.Response(500, json={"error": "Server error"}),
            httpx.Response(
                200,
                json={
                    "name": "sessions/test-123",
                    "state": "COMPLETED",
                    "createTime": "2024-01-01T00:00:00Z",
                    "updateTime": "2024-01-01T00:00:00Z",
                },
            ),
        ]

        async with JulesClient(api_key=api_key, retry_delay=0.01) as client:
            response = await client.get_session("test-123")

        assert response.state == SessionState.COMPLETED
        assert route.call_count == 2
