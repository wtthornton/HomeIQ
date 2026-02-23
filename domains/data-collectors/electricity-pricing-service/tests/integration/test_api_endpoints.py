"""
API Endpoint Integration Tests
Epic 49 Story 49.3: Integration Test Suite

Tests for all API endpoints including health checks and cheapest hours.
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.main import ElectricityPricingService, create_app


class TestAPIEndpoints(AioHTTPTestCase):
    """Integration tests for API endpoints"""
    
    async def get_application(self):
        """Create test application"""
        # Set test environment
        os.environ['INFLUXDB_TOKEN'] = 'test-token'
        os.environ['INFLUXDB_URL'] = 'http://test-influxdb:8086'
        os.environ['INFLUXDB_ORG'] = 'test-org'
        os.environ['INFLUXDB_BUCKET'] = 'test-bucket'
        
        # Create service with mocked dependencies
        service = ElectricityPricingService()
        
        # Mock InfluxDB client
        service.influxdb_client = MagicMock()
        service.influxdb_client.write = MagicMock()
        
        # Mock HTTP session
        service.session = AsyncMock()
        
        # Set cached data for testing
        service.cached_data = {
            'cheapest_hours': [
                {'hour': 2, 'price': 0.15},
                {'hour': 3, 'price': 0.16},
                {'hour': 4, 'price': 0.17},
                {'hour': 5, 'price': 0.18}
            ]
        }
        service.last_fetch_time = datetime.now(timezone.utc)
        
        return await create_app(service)
    
    @unittest_run_loop
    async def test_health_endpoint(self):
        """Test health check endpoint returns 200"""
        resp = await self.client.request("GET", "/health")
        
        assert resp.status == 200
        data = await resp.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    @unittest_run_loop
    async def test_cheapest_hours_endpoint_default(self):
        """Test cheapest hours endpoint with default hours"""
        # Test with internal network (should succeed)
        with patch('src.security.require_internal_network', new_callable=AsyncMock):
            resp = await self.client.request("GET", "/cheapest-hours")
            
            assert resp.status == 200
            data = await resp.json()
            assert "cheapest_hours" in data
            assert len(data["cheapest_hours"]) == 4  # Default hours
    
    @unittest_run_loop
    async def test_cheapest_hours_endpoint_with_hours_param(self):
        """Test cheapest hours endpoint with hours parameter"""
        with patch('src.security.require_internal_network', new_callable=AsyncMock):
            resp = await self.client.request("GET", "/cheapest-hours?hours=2")
            
            assert resp.status == 200
            data = await resp.json()
            assert "cheapest_hours" in data
            assert len(data["cheapest_hours"]) == 2
    
    @unittest_run_loop
    async def test_cheapest_hours_endpoint_invalid_hours(self):
        """Test cheapest hours endpoint with invalid hours parameter"""
        with patch('src.security.require_internal_network', new_callable=AsyncMock):
            # Test with hours > 24
            resp = await self.client.request("GET", "/cheapest-hours?hours=25")
            
            assert resp.status == 400
            data = await resp.json()
            assert "error" in data
            
            # Test with hours < 1
            resp = await self.client.request("GET", "/cheapest-hours?hours=0")
            
            assert resp.status == 400
            data = await resp.json()
            assert "error" in data
    
    @unittest_run_loop
    async def test_cheapest_hours_endpoint_non_integer(self):
        """Test cheapest hours endpoint with non-integer hours"""
        with patch('src.security.require_internal_network', new_callable=AsyncMock):
            resp = await self.client.request("GET", "/cheapest-hours?hours=abc")
            
            assert resp.status == 400
            data = await resp.json()
            assert "error" in data
    
    @unittest_run_loop
    async def test_cheapest_hours_endpoint_no_data(self):
        """Test cheapest hours endpoint when no data available"""
        # Create new service without cached data
        os.environ['INFLUXDB_TOKEN'] = 'test-token'
        service = ElectricityPricingService()
        service.influxdb_client = MagicMock()
        service.session = AsyncMock()
        service.cached_data = None  # No cached data
        
        app = await create_app(service)
        
        # Create new test client
        from aiohttp.test_utils import TestClient
        async with TestClient(app) as client:
            with patch('src.security.require_internal_network', new_callable=AsyncMock):
                resp = await client.request("GET", "/cheapest-hours")
                
                assert resp.status == 503
                data = await resp.json()
                assert "error" in data
    
    @unittest_run_loop
    async def test_cheapest_hours_endpoint_internal_network_required(self):
        """Test cheapest hours endpoint requires internal network"""
        # Test with external network (should fail)
        with patch('src.security.require_internal_network', side_effect=web.HTTPForbidden()):
            resp = await self.client.request("GET", "/cheapest-hours")
            
            assert resp.status == 403


@pytest.mark.asyncio
async def test_service_startup_with_missing_token():
    """Test service fails fast on missing InfluxDB token"""
    # Remove token from environment
    if 'INFLUXDB_TOKEN' in os.environ:
        del os.environ['INFLUXDB_TOKEN']
    
    with pytest.raises(ValueError) as exc_info:
        service = ElectricityPricingService()
    
    assert "INFLUXDB_TOKEN" in str(exc_info.value)


@pytest.mark.asyncio
async def test_service_startup_with_valid_config():
    """Test service starts successfully with valid configuration"""
    os.environ['INFLUXDB_TOKEN'] = 'test-token'
    os.environ['INFLUXDB_URL'] = 'http://test-influxdb:8086'
    os.environ['INFLUXDB_ORG'] = 'test-org'
    os.environ['INFLUXDB_BUCKET'] = 'test-bucket'
    
    service = ElectricityPricingService()
    assert service.influxdb_bucket == 'test-bucket'
    
    # Cleanup
    try:
        await service.shutdown()
    except:
        pass

