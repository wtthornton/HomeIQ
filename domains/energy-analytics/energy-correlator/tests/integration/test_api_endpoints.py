"""
API Endpoint Integration Tests
Epic 48 Story 48.2: Integration Test Suite

Tests for all API endpoints including health checks, statistics, and security.
Converted from aiohttp TestCase to FastAPI TestClient.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch):
    """Set required environment variables for all tests."""
    monkeypatch.setenv('INFLUXDB_TOKEN', 'test-token')
    monkeypatch.setenv('INFLUXDB_URL', 'http://test-influxdb:8086')
    monkeypatch.setenv('INFLUXDB_ORG', 'test-org')
    monkeypatch.setenv('INFLUXDB_BUCKET', 'test-bucket')
    monkeypatch.setenv('PROCESSING_INTERVAL', '10')
    monkeypatch.setenv('LOOKBACK_MINUTES', '5')


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    from src.main import app
    return TestClient(app)


class TestAPIEndpoints:
    """Integration tests for API endpoints"""

    def test_health_endpoint(self, client):
        """Test health check endpoint returns 200"""
        resp = client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_statistics_endpoint_returns_response(self, client):
        """Test statistics endpoint returns a response."""
        resp = client.get("/statistics")
        # Without a running service, it returns 503
        assert resp.status_code in [200, 503]

    def test_reset_statistics_endpoint_without_service(self, client):
        """Test reset statistics endpoint when service is not initialized."""
        resp = client.post("/statistics/reset")
        # Without a running service, it returns 503
        assert resp.status_code == 503

    def test_reset_statistics_endpoint_method_validation(self, client):
        """Test reset endpoint only accepts POST"""
        resp = client.get("/statistics/reset")
        assert resp.status_code == 405  # Method not allowed


@pytest.mark.asyncio
async def test_service_startup_with_invalid_bucket(monkeypatch):
    """Test validate_bucket_name rejects invalid names"""
    from src.security import validate_bucket_name

    with pytest.raises(ValueError) as exc_info:
        validate_bucket_name("invalid bucket name!")

    assert "bucket" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_service_startup_with_valid_bucket():
    """Test validate_bucket_name accepts valid names"""
    from src.security import validate_bucket_name

    result = validate_bucket_name("valid-bucket-name")
    assert result == "valid-bucket-name"
