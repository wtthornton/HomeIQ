"""
Security Validation Tests
Epic 48 Story 48.1: Security Hardening & Input Validation

Tests for bucket name validation and internal request validation.
"""

import pytest
from unittest.mock import Mock

from src.security import validate_bucket_name, validate_internal_request


class TestBucketNameValidation:
    """Tests for validate_bucket_name() function"""
    
    def test_valid_bucket_names(self):
        """Test that valid bucket names pass validation"""
        valid_names = [
            "home_assistant_events",
            "test-bucket-123",
            "bucket_name",
            "Bucket123",
            "a",
            "a" * 255,  # Max length
        ]
        
        for name in valid_names:
            # Should not raise
            validate_bucket_name(name)
    
    def test_empty_bucket_name(self):
        """Test that empty bucket name raises ValueError"""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_bucket_name("")
    
    def test_none_bucket_name(self):
        """Test that None bucket name raises ValueError"""
        with pytest.raises(ValueError):
            validate_bucket_name(None)
    
    def test_invalid_characters(self):
        """Test that bucket names with invalid characters raise ValueError"""
        invalid_names = [
            "bucket with spaces",
            "bucket@name",
            "bucket.name",
            "bucket#name",
            "bucket$name",
            "bucket%name",
            "bucket&name",
            "bucket*name",
            "bucket+name",
            "bucket=name",
            "bucket[name]",
            "bucket{name}",
            "bucket|name",
            "bucket\\name",
            "bucket/name",
            "bucket?name",
            "bucket!name",
            "bucket~name",
            "bucket`name",
            "bucket'name",
            'bucket"name',
        ]
        
        for name in invalid_names:
            with pytest.raises(ValueError, match="Invalid bucket name format"):
                validate_bucket_name(name)
    
    def test_too_long_bucket_name(self):
        """Test that bucket names exceeding 255 characters raise ValueError"""
        long_name = "a" * 256  # Exceeds max length
        
        with pytest.raises(ValueError, match="exceeds maximum length"):
            validate_bucket_name(long_name)
    
    def test_error_message_clarity(self):
        """Test that error messages are clear and actionable"""
        with pytest.raises(ValueError) as exc_info:
            validate_bucket_name("invalid bucket name")
        
        error_message = str(exc_info.value)
        assert "Invalid bucket name format" in error_message
        assert "invalid bucket name" in error_message
        assert "alphanumeric" in error_message.lower()


class TestInternalRequestValidation:
    """Tests for validate_internal_request() function"""
    
    def test_private_ip_ranges(self):
        """Test that private IP ranges are accepted"""
        private_ips = [
            "10.0.0.1",
            "172.16.0.1",
            "192.168.1.1",
            "127.0.0.1",
            "172.17.0.1",  # Docker default
        ]
        
        for ip in private_ips:
            request = self._create_mock_request(ip)
            assert validate_internal_request(request) is True, f"IP {ip} should be accepted"
    
    def test_public_ip_rejected(self):
        """Test that public IP addresses are rejected"""
        public_ips = [
            "8.8.8.8",  # Google DNS
            "1.1.1.1",  # Cloudflare DNS
            "203.0.113.1",  # Example public IP
        ]
        
        for ip in public_ips:
            request = self._create_mock_request(ip)
            assert validate_internal_request(request) is False, f"IP {ip} should be rejected"
    
    def test_custom_allowed_networks(self):
        """Test that custom allowed networks work"""
        # Allow a specific public IP range for testing
        custom_networks = ["203.0.113.0/24"]
        
        request = self._create_mock_request("203.0.113.1")
        assert validate_internal_request(request, custom_networks) is True
    
    def test_custom_networks_override(self):
        """Test that custom networks extend default internal networks"""
        # Even with custom networks, private IPs should still work
        custom_networks = ["203.0.113.0/24"]
        
        request = self._create_mock_request("192.168.1.1")
        assert validate_internal_request(request, custom_networks) is True
    
    def test_invalid_ip_format(self):
        """Test that invalid IP formats are rejected"""
        invalid_ips = [
            "not.an.ip.address",
            "256.256.256.256",
            "",
            None,
        ]
        
        for ip in invalid_ips:
            request = self._create_mock_request(ip)
            assert validate_internal_request(request) is False
    
    def test_ip_with_port(self):
        """Test that IP addresses with port numbers are handled correctly"""
        # aiohttp request.remote format: "IP:PORT"
        request = self._create_mock_request("192.168.1.1:54321")
        assert validate_internal_request(request) is True
    
    def test_none_remote(self):
        """Test that None remote is rejected"""
        request = Mock()
        request.remote = None
        assert validate_internal_request(request) is False
    
    def test_empty_remote(self):
        """Test that empty remote is rejected"""
        request = Mock()
        request.remote = ""
        assert validate_internal_request(request) is False
    
    def test_invalid_network_format(self):
        """Test that invalid network formats in allowed_networks are handled gracefully"""
        # Should not crash, just skip invalid networks
        invalid_networks = ["not.a.network", "256.256.256.256/24"]
        
        request = self._create_mock_request("192.168.1.1")
        # Should still work with default internal networks
        assert validate_internal_request(request, invalid_networks) is True
    
    def _create_mock_request(self, remote: str):
        """Helper to create mock aiohttp request with remote IP"""
        request = Mock()
        request.remote = remote
        return request

