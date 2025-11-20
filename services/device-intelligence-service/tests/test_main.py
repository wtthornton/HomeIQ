"""
Device Intelligence Service - Main App Tests

Tests for the main FastAPI application.
"""

from fastapi.testclient import TestClient


class TestMainApp:
    """Test main FastAPI application."""

    def test_app_creation(self, client: TestClient):
        """Test that the FastAPI app is created correctly."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Device Intelligence Service"
        assert data["version"] == "1.0.0"

    def test_cors_middleware(self, client: TestClient):
        """Test CORS middleware is configured."""
        response = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers

    def test_error_handling(self, client: TestClient):
        """Test error handling middleware."""
        # Test with a non-existent device ID to trigger 404
        response = client.get("/api/devices/invalid-device-id")
        assert response.status_code == 404
        assert "Device not found" in response.json()["detail"]

    def test_api_documentation(self, client: TestClient):
        """Test that API documentation is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_documentation(self, client: TestClient):
        """Test that ReDoc documentation is accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200
