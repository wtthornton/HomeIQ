"""
API Endpoint Integration Tests
Epic 48 Story 48.2: Integration Test Suite

Tests for all API endpoints including health checks, statistics, and security.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.main import EnergyCorrelatorService, create_app


class TestAPIEndpoints(AioHTTPTestCase):
    """Integration tests for API endpoints"""
    
    async def get_application(self):
        """Create test application"""
        # Set test environment
        os.environ['INFLUXDB_TOKEN'] = 'test-token'
        os.environ['INFLUXDB_URL'] = 'http://test-influxdb:8086'
        os.environ['INFLUXDB_ORG'] = 'test-org'
        os.environ['INFLUXDB_BUCKET'] = 'test-bucket'
        os.environ['PROCESSING_INTERVAL'] = '10'
        os.environ['LOOKBACK_MINUTES'] = '5'
        
        # Create service with mocked correlator
        service = EnergyCorrelatorService()
        
        # Mock the correlator's InfluxDB client to avoid real connections
        service.correlator.client = MagicMock()
        service.correlator.client.query = AsyncMock(return_value=[])
        
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
    async def test_statistics_endpoint_public_access(self):
        """Test statistics endpoint is publicly accessible"""
        resp = await self.client.request("GET", "/statistics")
        
        assert resp.status == 200
        data = await resp.json()
        assert isinstance(data, dict)
        # Statistics should contain correlation metrics
        assert "total_correlations" in data or "events_processed" in data
    
    @unittest_run_loop
    async def test_reset_statistics_endpoint_internal_only(self):
        """Test reset statistics endpoint requires internal network"""
        # Test with external IP (should fail)
        with patch('src.security.validate_internal_request', return_value=False):
            resp = await self.client.request("POST", "/statistics/reset")
            
            assert resp.status == 403
            data = await resp.json()
            assert "error" in data
            assert "internal networks" in data["error"].lower()
    
    @unittest_run_loop
    async def test_reset_statistics_endpoint_internal_success(self):
        """Test reset statistics endpoint works from internal network"""
        # Test with internal IP (should succeed)
        with patch('src.security.validate_internal_request', return_value=True):
            resp = await self.client.request("POST", "/statistics/reset")
            
            assert resp.status == 200
            data = await resp.json()
            assert "message" in data
            assert "reset" in data["message"].lower()
    
    @unittest_run_loop
    async def test_reset_statistics_endpoint_method_validation(self):
        """Test reset endpoint only accepts POST"""
        # GET should fail
        resp = await self.client.request("GET", "/statistics/reset")
        assert resp.status == 405  # Method not allowed
    
    @unittest_run_loop
    async def test_statistics_endpoint_after_reset(self):
        """Test statistics endpoint after reset"""
        # Reset statistics
        with patch('src.security.validate_internal_request', return_value=True):
            await self.client.request("POST", "/statistics/reset")
        
        # Get statistics (should be reset)
        resp = await self.client.request("GET", "/statistics")
        assert resp.status == 200
        data = await resp.json()
        assert isinstance(data, dict)


class TestAPIEndpointErrorHandling(AioHTTPTestCase):
    """Test error handling in API endpoints"""
    
    async def get_application(self):
        """Create test application with error scenarios"""
        os.environ['INFLUXDB_TOKEN'] = 'test-token'
        os.environ['INFLUXDB_URL'] = 'http://test-influxdb:8086'
        os.environ['INFLUXDB_ORG'] = 'test-org'
        os.environ['INFLUXDB_BUCKET'] = 'test-bucket'
        
        service = EnergyCorrelatorService()
        
        # Mock correlator to raise errors
        service.correlator.get_statistics = MagicMock(side_effect=Exception("Test error"))
        service.correlator.client = MagicMock()
        
        return await create_app(service)
    
    @unittest_run_loop
    async def test_statistics_endpoint_error_handling(self):
        """Test statistics endpoint handles errors gracefully"""
        resp = await self.client.request("GET", "/statistics")
        
        # Should return 500 or handle error gracefully
        assert resp.status in [200, 500]
        
        if resp.status == 500:
            data = await resp.json()
            assert "error" in data


@pytest.mark.asyncio
async def test_service_startup_with_invalid_bucket():
    """Test service fails fast on invalid bucket name"""
    os.environ['INFLUXDB_TOKEN'] = 'test-token'
    os.environ['INFLUXDB_BUCKET'] = 'invalid bucket name!'  # Invalid: contains space
    
    with pytest.raises(ValueError) as exc_info:
        service = EnergyCorrelatorService()
    
    assert "bucket" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_service_startup_with_valid_bucket():
    """Test service starts successfully with valid bucket name"""
    os.environ['INFLUXDB_TOKEN'] = 'test-token'
    os.environ['INFLUXDB_BUCKET'] = 'valid-bucket-name'
    
    service = EnergyCorrelatorService()
    assert service.influxdb_bucket == 'valid-bucket-name'
    
    # Cleanup
    try:
        await service.shutdown()
    except:
        pass


