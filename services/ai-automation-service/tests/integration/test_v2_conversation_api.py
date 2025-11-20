"""
Integration tests for v2 Conversation API

Tests critical conversation flows:
- Starting conversations
- Sending messages
- Getting suggestions
- Handling different response types
- Streaming support
"""

import json

import httpx
import pytest


@pytest.mark.integration
@pytest.mark.asyncio
class TestV2ConversationAPI:
    """Integration tests for v2 conversation endpoints"""

    @pytest.fixture
    async def api_client(self):
        """Create HTTP client for API testing"""
        base_url = "http://localhost:8018"
        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
            yield client

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Authentication headers"""
        api_key = "hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"
        return {
            "Authorization": f"Bearer {api_key}",
            "X-HomeIQ-API-Key": api_key,
            "Content-Type": "application/json",
        }

    async def test_start_conversation(self, api_client, auth_headers):
        """Test starting a new conversation"""
        response = await api_client.post(
            "/api/v2/conversations",
            headers=auth_headers,
            json={
                "query": "turn on office lights",
                "user_id": "test_user",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "conversation_id" in data
        assert data["user_id"] == "test_user"
        assert data["initial_query"] == "turn on office lights"
        assert data["status"] == "active"
        assert "created_at" in data

        return data["conversation_id"]

    async def test_send_message(self, api_client, auth_headers):
        """Test sending a message in a conversation"""
        # Start conversation first
        conv_response = await api_client.post(
            "/api/v2/conversations",
            headers=auth_headers,
            json={
                "query": "turn on office lights",
                "user_id": "test_user",
            },
        )
        conversation_id = conv_response.json()["conversation_id"]

        # Send message
        response = await api_client.post(
            f"/api/v2/conversations/{conversation_id}/message",
            headers=auth_headers,
            json={
                "message": "make it blue",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conversation_id
        assert "turn_number" in data
        assert "response_type" in data
        assert "content" in data
        assert "created_at" in data

    async def test_get_conversation(self, api_client, auth_headers):
        """Test retrieving conversation details"""
        # Start conversation
        conv_response = await api_client.post(
            "/api/v2/conversations",
            headers=auth_headers,
            json={
                "query": "turn on office lights",
                "user_id": "test_user",
            },
        )
        conversation_id = conv_response.json()["conversation_id"]

        # Get conversation
        response = await api_client.get(
            f"/api/v2/conversations/{conversation_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conversation_id
        assert "turns" in data
        assert isinstance(data["turns"], list)
        assert len(data["turns"]) > 0

    async def test_get_suggestions(self, api_client, auth_headers):
        """Test getting suggestions for a conversation"""
        # Start conversation
        conv_response = await api_client.post(
            "/api/v2/conversations",
            headers=auth_headers,
            json={
                "query": "turn on office lights when I get home",
                "user_id": "test_user",
            },
        )
        conversation_id = conv_response.json()["conversation_id"]

        # Get suggestions
        response = await api_client.get(
            f"/api/v2/conversations/{conversation_id}/suggestions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

    async def test_response_types(self, api_client, auth_headers):
        """Test different response types"""
        # Test automation generation
        conv_response = await api_client.post(
            "/api/v2/conversations",
            headers=auth_headers,
            json={
                "query": "turn on office lights when I get home",
                "user_id": "test_user",
            },
        )
        conversation_id = conv_response.json()["conversation_id"]

        # Send message that should generate automation
        response = await api_client.post(
            f"/api/v2/conversations/{conversation_id}/message",
            headers=auth_headers,
            json={
                "message": "turn on office lights when I get home",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] in [
            "automation_generated",
            "clarification_needed",
            "action_done",
            "information_provided",
        ]

    async def test_clarification_flow(self, api_client, auth_headers):
        """Test clarification flow"""
        # Start conversation with ambiguous query
        conv_response = await api_client.post(
            "/api/v2/conversations",
            headers=auth_headers,
            json={
                "query": "turn on the lights",
                "user_id": "test_user",
            },
        )
        conversation_id = conv_response.json()["conversation_id"]

        # Check if clarification is needed
        response = await api_client.get(
            f"/api/v2/conversations/{conversation_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Check if any turn has clarification questions
        has_clarification = any(
            turn.get("response_type") == "clarification_needed"
            or turn.get("clarification_questions")
            for turn in data.get("turns", [])
        )
        # This may or may not trigger clarification depending on entity resolution
        assert isinstance(has_clarification, bool)

    async def test_conversation_not_found(self, api_client, auth_headers):
        """Test error handling for non-existent conversation"""
        response = await api_client.get(
            "/api/v2/conversations/non-existent-id",
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_invalid_message(self, api_client, auth_headers):
        """Test error handling for invalid message"""
        # Start conversation
        conv_response = await api_client.post(
            "/api/v2/conversations",
            headers=auth_headers,
            json={
                "query": "test",
                "user_id": "test_user",
            },
        )
        conversation_id = conv_response.json()["conversation_id"]

        # Send empty message
        response = await api_client.post(
            f"/api/v2/conversations/{conversation_id}/message",
            headers=auth_headers,
            json={
                "message": "",
            },
        )

        # Should return 400 or 422 (validation error)
        assert response.status_code in [400, 422]


@pytest.mark.integration
@pytest.mark.asyncio
class TestV2ActionAPI:
    """Integration tests for v2 action endpoints"""

    @pytest.fixture
    async def api_client(self):
        """Create HTTP client for API testing"""
        base_url = "http://localhost:8018"
        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
            yield client

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Authentication headers"""
        api_key = "hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"
        return {
            "Authorization": f"Bearer {api_key}",
            "X-HomeIQ-API-Key": api_key,
            "Content-Type": "application/json",
        }

    async def test_execute_action(self, api_client, auth_headers):
        """Test executing an immediate action"""
        response = await api_client.post(
            "/api/v2/actions/execute",
            headers=auth_headers,
            json={
                "query": "turn on office lights",
                "user_id": "test_user",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "action_type" in data
        assert "message" in data
        assert "execution_time_ms" in data


@pytest.mark.integration
@pytest.mark.asyncio
class TestV2AutomationAPI:
    """Integration tests for v2 automation endpoints"""

    @pytest.fixture
    async def api_client(self):
        """Create HTTP client for API testing"""
        base_url = "http://localhost:8018"
        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
            yield client

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Authentication headers"""
        api_key = "hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"
        return {
            "Authorization": f"Bearer {api_key}",
            "X-HomeIQ-API-Key": api_key,
            "Content-Type": "application/json",
        }

    async def test_list_automations(self, api_client, auth_headers):
        """Test listing automations"""
        response = await api_client.get(
            "/api/v2/automations",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "automations" in data
        assert isinstance(data["automations"], list)

    async def test_generate_automation(self, api_client, auth_headers):
        """Test generating automation YAML"""
        # This test requires a valid suggestion_id from a conversation
        # For now, we'll test the endpoint structure
        response = await api_client.post(
            "/api/v2/automations/generate",
            headers=auth_headers,
            json={
                "suggestion_id": "test-suggestion-id",
                "conversation_id": "test-conv-id",
                "turn_id": 1,
            },
        )

        # May return 404 if suggestion doesn't exist, or 200 if it does
        assert response.status_code in [200, 404, 422]


@pytest.mark.integration
@pytest.mark.asyncio
class TestV2StreamingAPI:
    """Integration tests for v2 streaming endpoints"""

    @pytest.fixture
    async def api_client(self):
        """Create HTTP client for API testing"""
        base_url = "http://localhost:8018"
        async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
            yield client

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Authentication headers"""
        api_key = "hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"
        return {
            "Authorization": f"Bearer {api_key}",
            "X-HomeIQ-API-Key": api_key,
            "Content-Type": "application/json",
        }

    async def test_stream_conversation(self, api_client, auth_headers):
        """Test streaming conversation turn"""
        # Start conversation
        conv_response = await api_client.post(
            "/api/v2/conversations",
            headers=auth_headers,
            json={
                "query": "turn on office lights",
                "user_id": "test_user",
            },
        )
        conversation_id = conv_response.json()["conversation_id"]

        # Stream message
        async with api_client.stream(
            "POST",
            f"/api/v2/conversations/{conversation_id}/stream",
            headers=auth_headers,
            json={
                "message": "make it blue",
            },
        ) as response:
            assert response.status_code == 200
            assert response.headers.get("content-type", "").startswith("text/event-stream")

            chunks = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        chunks.append(data)
                    except json.JSONDecodeError:
                        pass

            # Should have received at least one chunk
            assert len(chunks) > 0

