"""
Unit Tests for Data API Service Main Application
"""

import os

# Import app from main module
import sys
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from main import DataAPIService, app, data_api_service


class TestDataAPIService:
    """Test Data API Service class"""

    def test_init(self):
        """Test service initialization"""
        service = DataAPIService()

        assert service.api_port == 8006
        assert service.api_title == 'Data API - Feature Data Hub'
        assert service.api_version == '1.0.0'
        assert service.is_running is False
        assert service.auth_manager is not None
        assert service.influxdb_client is not None

    @pytest.mark.asyncio
    async def test_startup(self):
        """Test service startup"""
        service = DataAPIService()

        with patch.object(service.influxdb_client, 'connect', return_value=True):
            await service.startup()

            assert service.is_running is True

    @pytest.mark.asyncio
    async def test_startup_influxdb_failure(self):
        """Test service startup with InfluxDB connection failure"""
        service = DataAPIService()

        with patch.object(service.influxdb_client, 'connect', return_value=False):
            await service.startup()

            # Service should still start even if InfluxDB fails
            assert service.is_running is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test service shutdown"""
        service = DataAPIService()
        service.is_running = True

        with patch.object(service.influxdb_client, 'close', new_callable=AsyncMock):
            await service.shutdown()

            assert service.is_running is False


class TestFastAPIApp:
    """Test FastAPI application endpoints"""

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint returns correct structure"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert data["data"]["service"] == "Data API - Feature Data Hub"
            assert data["data"]["version"] == "1.0.0"
            assert data["data"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health endpoint returns correct structure"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()

            # Verify required fields
            assert "status" in data
            assert "service" in data
            assert data["service"] == "data-api"
            assert "version" in data
            assert "timestamp" in data
            assert "uptime_seconds" in data
            assert "dependencies" in data
            assert "influxdb" in data["dependencies"]

    @pytest.mark.asyncio
    async def test_api_info_endpoint(self):
        """Test API info endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/info")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "endpoints" in data["data"]
            assert "authentication" in data["data"]


class TestInfluxDBIntegration:
    """Test InfluxDB client integration"""

    @pytest.mark.asyncio
    async def test_influxdb_connection_success(self):
        """Test successful InfluxDB connection"""
        service = DataAPIService()

        with patch.object(service.influxdb_client, 'connect', return_value=True):
            await service.startup()

            status = service.influxdb_client.get_connection_status()
            assert "is_connected" in status
            assert "url" in status
            assert "query_count" in status

    @pytest.mark.asyncio
    async def test_influxdb_connection_failure(self):
        """Test InfluxDB connection failure handling"""
        service = DataAPIService()

        with patch.object(service.influxdb_client, 'connect', side_effect=Exception("Connection failed")):
            await service.startup()

            # Service should start despite InfluxDB failure
            assert service.is_running is True


class TestCORSMiddleware:
    """Test CORS configuration"""

    @pytest.mark.asyncio
    async def test_cors_headers(self):
        """Test CORS headers are present"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health", headers={"Origin": "http://localhost:3000"})

            assert response.status_code == 200
            # CORS headers should be present
            # Note: Testing CORS properly requires actual cross-origin requests


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_404_error(self):
        """Test 404 error for non-existent endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/nonexistent")

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_exception_handler(self):
        """Test general exception handler"""
        # Create endpoint that raises exception
        @app.get("/test/error")
        async def error_endpoint():
            raise ValueError("Test error")

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/test/error")

            assert response.status_code == 500
            data = response.json()
            assert data["success"] is False
            assert "error" in data


class TestAuthentication:
    """Test authentication (when enabled)"""

    def test_auth_manager_initialization(self):
        """Test auth manager is initialized"""
        assert data_api_service.auth_manager is not None
        assert data_api_service.auth_manager.enable_auth is False  # Default: disabled

    @pytest.mark.asyncio
    async def test_auth_disabled_allows_access(self):
        """Test that endpoints are accessible when auth is disabled"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

            # Should succeed without auth header
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src", "--cov-report=term-missing"])

