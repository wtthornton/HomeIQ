"""
Authentication tests for AI Automation Service.

Tests that all routes are properly protected by authentication middleware.
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    """Get a valid API key from environment or use test key."""
    import os
    return os.getenv("AI_AUTOMATION_API_KEY", "test-api-key")


@pytest.fixture
def invalid_api_key():
    """Get an invalid API key for testing."""
    return "invalid-api-key"


class TestAuthentication:
    """Test suite for authentication middleware."""

    def test_public_paths_accessible(self, client):
        """Test that public paths are accessible without authentication."""
        # Health endpoint should be accessible
        response = client.get("/health")
        assert response.status_code == 200

        # Docs should be accessible
        response = client.get("/docs")
        assert response.status_code == 200

    def test_ask_ai_query_requires_auth(self, client, valid_api_key, invalid_api_key):
        """Test that /api/v1/ask-ai/query requires authentication."""
        # Without API key
        response = client.post(
            "/api/v1/ask-ai/query",
            json={"query": "test query"}
        )
        assert response.status_code == 401
        assert "Unauthorized" in response.json()["error"]

        # With invalid API key
        response = client.post(
            "/api/v1/ask-ai/query",
            json={"query": "test query"},
            headers={"X-HomeIQ-API-Key": invalid_api_key}
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

        # With valid API key (if configured)
        if valid_api_key != "test-api-key":
            response = client.post(
                "/api/v1/ask-ai/query",
                json={"query": "test query"},
                headers={"X-HomeIQ-API-Key": valid_api_key}
            )
            # Should not be 401 (may be 400 or 500 depending on service state)
            assert response.status_code != 401

    def test_ask_ai_clarify_requires_auth(self, client, invalid_api_key):
        """Test that /api/v1/ask-ai/clarify requires authentication."""
        response = client.post(
            "/api/v1/ask-ai/clarify",
            json={"session_id": "test", "answer": "test"}
        )
        assert response.status_code == 401

        response = client.post(
            "/api/v1/ask-ai/clarify",
            json={"session_id": "test", "answer": "test"},
            headers={"X-HomeIQ-API-Key": invalid_api_key}
        )
        assert response.status_code == 401

    def test_ask_ai_suggestions_requires_auth(self, client, invalid_api_key):
        """Test that /api/v1/ask-ai/query/{query_id}/suggestions requires authentication."""
        response = client.get("/api/v1/ask-ai/query/test-query-id/suggestions")
        assert response.status_code == 401

        response = client.get(
            "/api/v1/ask-ai/query/test-query-id/suggestions",
            headers={"X-HomeIQ-API-Key": invalid_api_key}
        )
        assert response.status_code == 401

    def test_ask_ai_approve_requires_auth(self, client, invalid_api_key):
        """Test that /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/approve requires authentication."""
        response = client.post(
            "/api/v1/ask-ai/query/test-query-id/suggestions/test-suggestion-id/approve"
        )
        assert response.status_code == 401

        response = client.post(
            "/api/v1/ask-ai/query/test-query-id/suggestions/test-suggestion-id/approve",
            headers={"X-HomeIQ-API-Key": invalid_api_key}
        )
        assert response.status_code == 401

    def test_bearer_token_auth(self, client, valid_api_key, invalid_api_key):
        """Test that Bearer token authentication works."""
        # Without token
        response = client.post(
            "/api/v1/ask-ai/query",
            json={"query": "test query"}
        )
        assert response.status_code == 401

        # With invalid Bearer token
        response = client.post(
            "/api/v1/ask-ai/query",
            json={"query": "test query"},
            headers={"Authorization": f"Bearer {invalid_api_key}"}
        )
        assert response.status_code == 401

        # With valid Bearer token (if configured)
        if valid_api_key != "test-api-key":
            response = client.post(
                "/api/v1/ask-ai/query",
                json={"query": "test query"},
                headers={"Authorization": f"Bearer {valid_api_key}"}
            )
            assert response.status_code != 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

