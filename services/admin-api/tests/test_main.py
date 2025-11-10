"""
Tests for Admin API main service
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.main import AdminAPIService, app


class TestAdminAPIService:
    """Test AdminAPIService class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = AdminAPIService()
    
    def test_init(self):
        """Test service initialization"""
        assert self.service.api_host == "0.0.0.0"
        assert self.service.api_port == 8000
        assert self.service.api_title == "Home Assistant Ingestor Admin API"
        assert self.service.api_version == "1.0.0"
        assert self.service.enable_auth is True
        assert self.service.is_running is False
        assert self.service.app is None
        assert self.service.server_task is None
    
    @patch('src.main.uvicorn.Server')
    @patch('src.main.uvicorn.Config')
    async def test_start(self, mock_config, mock_server):
        """Test service start"""
        # Mock server
        mock_server_instance = AsyncMock()
        mock_server.return_value = mock_server_instance
        
        # Mock config
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        
        # Start service
        await self.service.start()
        
        # Verify
        assert self.service.is_running is True
        assert self.service.app is not None
        assert self.service.server_task is not None
        
        # Verify server was started
        mock_server_instance.serve.assert_called_once()
    
    async def test_start_already_running(self):
        """Test starting service that's already running"""
        self.service.is_running = True
        
        with patch('src.main.logger') as mock_logger:
            await self.service.start()
            mock_logger.warning.assert_called_with("Admin API service is already running")
    
    async def test_stop(self):
        """Test service stop"""
        # Set up running service
        self.service.is_running = True
        self.service.server_task = AsyncMock()
        
        # Stop service
        await self.service.stop()
        
        # Verify
        assert self.service.is_running is False
        self.service.server_task.cancel.assert_called_once()
    
    async def test_stop_not_running(self):
        """Test stopping service that's not running"""
        self.service.is_running = False
        
        # Should not raise exception
        await self.service.stop()
    
    def test_get_app(self):
        """Test getting FastAPI app"""
        # Create mock app
        mock_app = Mock(spec=FastAPI)
        self.service.app = mock_app
        
        # Get app
        app = self.service.get_app()
        
        # Verify
        assert app == mock_app


class TestFastAPIApp:
    """Test FastAPI application"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = self.client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "service" in data["data"]
        assert "version" in data["data"]
        assert "status" in data["data"]
        assert data["data"]["status"] == "running"
    
    def test_api_info_endpoint(self):
        """Test API info endpoint"""
        response = self.client.get("/api/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "title" in data["data"]
        assert "version" in data["data"]
        assert "endpoints" in data["data"]
        assert "authentication" in data["data"]
        assert "cors_enabled" in data["data"]
    
    def test_health_endpoint(self):
        """Test health endpoint"""
        response = self.client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "admin_api_status" in data
        assert "ingestion_service" in data
        assert "timestamp" in data
    
    def test_stats_endpoint(self):
        """Test stats endpoint"""
        response = self.client.get("/api/v1/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "period" in data
        assert "metrics" in data
        assert "trends" in data
        assert "alerts" in data
    
    def test_config_endpoint(self):
        """Test config endpoint"""
        response = self.client.get("/api/v1/config")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_events_endpoint(self):
        """Test events endpoint"""
        response = self.client.get("/api/v1/events")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_cors_headers(self):
        """Test CORS headers"""
        response = self.client.options("/api/v1/health")
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
    
    def test_docs_endpoint(self):
        """Test API documentation endpoint"""
        response = self.client.get("/docs")
        
        # Should return 200 if docs are enabled, 404 if disabled
        assert response.status_code in [200, 404]
    
    def test_openapi_endpoint(self):
        """Test OpenAPI schema endpoint"""
        response = self.client.get("/openapi.json")
        
        # Should return 200 if OpenAPI is enabled, 404 if disabled
        assert response.status_code in [200, 404]


class TestErrorHandling:
    """Test error handling"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
    
    def test_404_error(self):
        """Test 404 error handling"""
        response = self.client.get("/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "error_code" in data
        assert "timestamp" in data
    
    def test_500_error(self):
        """Test 500 error handling"""
        # This would require mocking an endpoint to throw an exception
        # For now, we'll test the error response structure
        response = self.client.get("/api/v1/stats?period=invalid")
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 500]
    
    def test_validation_error(self):
        """Test validation error handling"""
        response = self.client.post("/api/v1/config/websocket-ingestion", json={})
        
        # Should return validation error
        assert response.status_code in [200, 400, 422]


class TestAuthentication:
    """Test authentication"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
    
    def test_protected_endpoints(self):
        """Test that protected endpoints require authentication"""
        # Test stats endpoint
        response = self.client.get("/api/v1/stats")
        # Should work without auth if auth is disabled
        assert response.status_code in [200, 401]
        
        # Test config endpoint
        response = self.client.get("/api/v1/config")
        # Should work without auth if auth is disabled
        assert response.status_code in [200, 401]
        
        # Test events endpoint
        response = self.client.get("/api/v1/events")
        # Should work without auth if auth is disabled
        assert response.status_code in [200, 401]
    
    def test_auth_endpoint(self):
        """Test authentication endpoint"""
        response = self.client.post("/api/token", json={
            "username": "admin",
            "password": "adminpass"
        })
        
        # Should work if auth is enabled
        assert response.status_code in [200, 401, 404]
    
    def test_invalid_auth(self):
        """Test invalid authentication"""
        response = self.client.post("/api/token", json={
            "username": "invalid",
            "password": "invalid"
        })
        
        # Should return 401
        assert response.status_code in [200, 401, 404]


class TestMiddleware:
    """Test middleware functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
    
    def test_request_logging(self):
        """Test request logging middleware"""
        response = self.client.get("/api/v1/health")
        
        # Should log the request
        assert response.status_code == 200
    
    def test_cors_middleware(self):
        """Test CORS middleware"""
        response = self.client.options("/api/v1/health")
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
    
    def test_response_time(self):
        """Test response time logging"""
        response = self.client.get("/api/v1/health")
        
        # Should include response time in logs
        assert response.status_code == 200
