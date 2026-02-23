"""
Security Tests
Epic 49 Story 49.1: Security Hardening & Input Validation

Tests for security validation functions.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest
from aiohttp import web

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.security import require_internal_network, validate_hours_parameter, validate_internal_request


class TestHoursParameterValidation:
    """Tests for hours parameter validation"""
    
    def test_valid_hours_in_range(self):
        """Test valid hours parameter within range"""
        assert validate_hours_parameter("4") == 4
        assert validate_hours_parameter("1") == 1
        assert validate_hours_parameter("24") == 24
        assert validate_hours_parameter("12") == 12
    
    def test_default_value_when_none(self):
        """Test default value when parameter is None"""
        assert validate_hours_parameter(None, default=4) == 4
        assert validate_hours_parameter(None, default=8) == 8
    
    def test_invalid_non_integer(self):
        """Test invalid non-integer values"""
        with pytest.raises(ValueError, match="Invalid hours parameter"):
            validate_hours_parameter("abc")
        
        with pytest.raises(ValueError, match="Invalid hours parameter"):
            validate_hours_parameter("12.5")
        
        with pytest.raises(ValueError, match="Invalid hours parameter"):
            validate_hours_parameter("")
    
    def test_out_of_range_low(self):
        """Test hours parameter below minimum"""
        with pytest.raises(ValueError, match="Hours parameter out of range"):
            validate_hours_parameter("0")
        
        with pytest.raises(ValueError, match="Hours parameter out of range"):
            validate_hours_parameter("-1")
    
    def test_out_of_range_high(self):
        """Test hours parameter above maximum"""
        with pytest.raises(ValueError, match="Hours parameter out of range"):
            validate_hours_parameter("25")
        
        with pytest.raises(ValueError, match="Hours parameter out of range"):
            validate_hours_parameter("100")


class TestInternalRequestValidation:
    """Tests for internal request validation"""
    
    def test_no_allowed_networks_allows_all(self):
        """Test that no allowed networks means all requests allowed"""
        request = MagicMock()
        request.remote = "192.168.1.100"
        
        assert validate_internal_request(request, None) is True
        assert validate_internal_request(request, []) is True
    
    def test_allowed_network_match(self):
        """Test request from allowed network"""
        request = MagicMock()
        request.remote = "192.168.1.100"
        
        allowed = ["192.168.0.0/16"]
        assert validate_internal_request(request, allowed) is True
    
    def test_allowed_network_no_match(self):
        """Test request from non-allowed network"""
        request = MagicMock()
        request.remote = "10.0.0.100"
        
        allowed = ["192.168.0.0/16"]
        assert validate_internal_request(request, allowed) is False
    
    def test_multiple_allowed_networks(self):
        """Test with multiple allowed networks"""
        request = MagicMock()
        request.remote = "172.16.1.100"
        
        allowed = ["192.168.0.0/16", "172.16.0.0/12"]
        assert validate_internal_request(request, allowed) is True
    
    def test_no_remote_address(self):
        """Test when remote address cannot be determined"""
        request = MagicMock()
        request.remote = None
        
        allowed = ["192.168.0.0/16"]
        assert validate_internal_request(request, allowed) is False
    
    def test_invalid_ip_address(self):
        """Test with invalid IP address"""
        request = MagicMock()
        request.remote = "invalid-ip"
        
        allowed = ["192.168.0.0/16"]
        # Should handle gracefully
        result = validate_internal_request(request, allowed)
        assert result is False
    
    def test_invalid_network_config(self):
        """Test with invalid network configuration"""
        request = MagicMock()
        request.remote = "192.168.1.100"
        
        allowed = ["invalid-network"]
        # Should handle gracefully
        result = validate_internal_request(request, allowed)
        assert result is False


class TestRequireInternalNetwork:
    """Tests for require_internal_network middleware"""
    
    @pytest.mark.asyncio
    async def test_allowed_network_passes(self):
        """Test that allowed network passes validation"""
        request = MagicMock()
        request.remote = "192.168.1.100"
        
        allowed = ["192.168.0.0/16"]
        
        # Should not raise exception
        await require_internal_network(request, allowed)
    
    @pytest.mark.asyncio
    async def test_no_allowed_networks_passes(self):
        """Test that no allowed networks means all requests pass"""
        request = MagicMock()
        request.remote = "10.0.0.100"
        
        # Should not raise exception
        await require_internal_network(request, None)
        await require_internal_network(request, [])
    
    @pytest.mark.asyncio
    async def test_non_allowed_network_raises_forbidden(self):
        """Test that non-allowed network raises HTTPForbidden"""
        request = MagicMock()
        request.remote = "10.0.0.100"
        
        allowed = ["192.168.0.0/16"]
        
        with pytest.raises(web.HTTPForbidden):
            await require_internal_network(request, allowed)

