"""Unit tests for ai-core-service main module endpoints and middleware."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_mocks():
    """Create the FastAPI app with mocked service manager."""
    from src.main import app

    mock_manager = MagicMock()
    mock_manager.get_service_status = AsyncMock(
        return_value={
            "openvino": {"healthy": True, "capabilities": ["embeddings"]},
            "ml": {"healthy": True, "capabilities": ["clustering"]},
        }
    )
    mock_manager.analyze_data = AsyncMock(
        return_value=({"embeddings": [[0.1]]}, ["openvino"])
    )
    mock_manager.detect_patterns = AsyncMock(
        return_value=([{"description": "test", "category": "automation"}], ["openvino"])
    )
    mock_manager.generate_suggestions = AsyncMock(
        return_value=([{"title": "Tip", "description": "Save energy"}], ["openai"])
    )

    app.state.service_manager = mock_manager
    app.state.api_key_value = "test-key"

    yield app

    app.state.service_manager = None
    app.state.api_key_value = None


@pytest.fixture
def client(app_with_mocks) -> TestClient:
    return TestClient(app_with_mocks)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"X-API-Key": "test-key"}


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ai-core-service"

    def test_health_starting_when_no_manager(self, client: TestClient, app_with_mocks) -> None:
        app_with_mocks.state.service_manager = None
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "starting"


class TestAnalyzeEndpoint:
    """Tests for the /analyze endpoint."""

    def test_analyze_requires_auth(self, client: TestClient) -> None:
        response = client.post("/analyze", json={
            "data": [{"x": 1}], "analysis_type": "basic",
        })
        assert response.status_code == 401

    def test_analyze_success(self, client: TestClient, auth_headers: dict) -> None:
        response = client.post("/analyze", json={
            "data": [{"x": 1}], "analysis_type": "basic",
        }, headers=auth_headers)
        assert response.status_code == 200
        assert "results" in response.json()

    def test_analyze_invalid_type(self, client: TestClient, auth_headers: dict) -> None:
        response = client.post("/analyze", json={
            "data": [{"x": 1}], "analysis_type": "invalid",
        }, headers=auth_headers)
        assert response.status_code == 422


class TestPatternsEndpoint:
    """Tests for the /patterns endpoint."""

    def test_detect_patterns_success(self, client: TestClient, auth_headers: dict) -> None:
        response = client.post("/patterns", json={
            "patterns": [{"description": "test"}], "detection_type": "full",
        }, headers=auth_headers)
        assert response.status_code == 200
        assert "detected_patterns" in response.json()


class TestSuggestionsEndpoint:
    """Tests for the /suggestions endpoint."""

    def test_suggestions_success(self, client: TestClient, auth_headers: dict) -> None:
        response = client.post("/suggestions", json={
            "context": {"devices": ["light"]},
            "suggestion_type": "energy_optimization",
        }, headers=auth_headers)
        assert response.status_code == 200
        assert "suggestions" in response.json()

    def test_suggestions_invalid_type(self, client: TestClient, auth_headers: dict) -> None:
        response = client.post("/suggestions", json={
            "context": {"devices": ["light"]},
            "suggestion_type": "bad_type",
        }, headers=auth_headers)
        assert response.status_code == 422


class TestRequestIdMiddleware:
    """Tests for request ID tracing middleware."""

    def test_adds_request_id(self, client: TestClient) -> None:
        response = client.get("/health")
        assert "X-Request-ID" in response.headers

    def test_preserves_provided_request_id(self, client: TestClient) -> None:
        response = client.get("/health", headers={"X-Request-ID": "custom-123"})
        assert response.headers["X-Request-ID"] == "custom-123"
