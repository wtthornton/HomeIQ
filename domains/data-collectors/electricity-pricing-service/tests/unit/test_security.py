"""
Security Tests
Epic 49 Story 49.1: Security Hardening & Input Validation

Tests for security validation functions.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "../.."))

from src.security import (
    require_internal_network,
    validate_hours_parameter,
    validate_internal_request,
)


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
    """Tests for internal request validation (reads request.client.host)"""

    @staticmethod
    def _request(host):
        request = MagicMock()
        request.client.host = host
        return request

    def test_no_allowed_networks_allows_all(self):
        """Test that no allowed networks means all requests allowed"""
        request = self._request("192.168.1.100")

        assert validate_internal_request(request, None) is True
        assert validate_internal_request(request, []) is True

    def test_allowed_network_match(self):
        """Test request from allowed network"""
        assert validate_internal_request(self._request("192.168.1.100"), ["192.168.0.0/16"]) is True

    def test_allowed_network_no_match(self):
        """Test request from non-allowed network"""
        assert validate_internal_request(self._request("10.0.0.100"), ["192.168.0.0/16"]) is False

    def test_multiple_allowed_networks(self):
        """Test with multiple allowed networks"""
        allowed = ["192.168.0.0/16", "172.16.0.0/12"]

        assert validate_internal_request(self._request("172.16.1.100"), allowed) is True

    def test_no_remote_address(self):
        """Test when remote address cannot be determined"""
        request = MagicMock()
        request.client = None

        assert validate_internal_request(request, ["192.168.0.0/16"]) is False

    def test_invalid_ip_address(self):
        """Test with invalid IP address"""
        assert validate_internal_request(self._request("invalid-ip"), ["192.168.0.0/16"]) is False

    def test_invalid_network_config(self):
        """Test with invalid network configuration"""
        assert (
            validate_internal_request(self._request("192.168.1.100"), ["invalid-network"]) is False
        )


class TestRequireInternalNetwork:
    """Tests for the require_internal_network guard (sync, raises HTTPException)"""

    @staticmethod
    def _request(host):
        request = MagicMock()
        request.client.host = host
        return request

    def test_allowed_network_passes(self):
        """Test that allowed network passes validation"""
        require_internal_network(self._request("192.168.1.100"), ["192.168.0.0/16"])

    def test_no_allowed_networks_passes(self):
        """Test that no allowed networks means all requests pass"""
        request = self._request("10.0.0.100")

        require_internal_network(request, None)
        require_internal_network(request, [])

    def test_non_allowed_network_raises_forbidden(self):
        """Test that non-allowed network raises a 403"""
        with pytest.raises(HTTPException) as exc_info:
            require_internal_network(self._request("10.0.0.100"), ["192.168.0.0/16"])

        assert exc_info.value.status_code == 403
