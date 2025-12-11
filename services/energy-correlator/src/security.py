"""
Security Validation Utilities
Epic 48 Story 48.1: Security Hardening & Input Validation

Provides validation functions for bucket names and internal request validation.
"""

import ipaddress
import re
from typing import Optional

# Import logger from main module when available
# This avoids circular imports - logger will be set after main module loads
logger = None  # Will be set by main module if needed


def validate_bucket_name(bucket_name: str) -> None:
    """
    Validate InfluxDB bucket name format.
    
    InfluxDB bucket names must:
    - Contain only alphanumeric characters, hyphens, and underscores
    - Not be empty
    - Not exceed reasonable length (255 characters)
    
    Args:
        bucket_name: The bucket name to validate
        
    Raises:
        ValueError: If bucket name is invalid with clear error message
    """
    if not bucket_name:
        raise ValueError("Bucket name cannot be empty")
    
    if len(bucket_name) > 255:
        raise ValueError(f"Bucket name exceeds maximum length (255 characters): {len(bucket_name)}")
    
    # InfluxDB bucket names: alphanumeric, hyphens, underscores only
    pattern = r'^[a-zA-Z0-9_-]+$'
    if not re.match(pattern, bucket_name):
        raise ValueError(
            f"Invalid bucket name format: '{bucket_name}'. "
            "Bucket names must contain only alphanumeric characters, hyphens, and underscores."
        )


def validate_internal_request(request, allowed_networks: Optional[list[str]] = None) -> bool:
    """
    Validate that request comes from internal network.
    
    Checks if the request's remote IP address is from an internal network.
    Internal networks include:
    - Private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    - Loopback (127.0.0.0/8)
    - Docker networks (172.17.0.0/16, 172.18.0.0/16, etc.)
    - Custom allowed networks from environment variable
    
    Args:
        request: aiohttp Request object
        allowed_networks: Optional list of CIDR networks to allow (from env var)
        
    Returns:
        True if request is from internal network, False otherwise
    """
    try:
        # Get client IP from request
        # aiohttp stores remote IP in request.remote
        remote_ip_str = request.remote
        
        # Handle case where remote might be None or in different format
        if not remote_ip_str:
            return False
            
        # Extract IP if remote is in format "IP:PORT"
        if ':' in remote_ip_str:
            remote_ip_str = remote_ip_str.split(':')[0]
        
        try:
            remote_ip = ipaddress.ip_address(remote_ip_str)
        except ValueError:
            # Invalid IP address
            return False
        
        # Default internal networks
        internal_networks = [
            ipaddress.ip_network('10.0.0.0/8'),
            ipaddress.ip_network('172.16.0.0/12'),
            ipaddress.ip_network('192.168.0.0/16'),
            ipaddress.ip_network('127.0.0.0/8'),
            # Docker default networks
            ipaddress.ip_network('172.17.0.0/16'),
            ipaddress.ip_network('172.18.0.0/16'),
            ipaddress.ip_network('172.19.0.0/16'),
            ipaddress.ip_network('172.20.0.0/16'),
        ]
        
        # Add custom allowed networks if provided
        if allowed_networks:
            for network_str in allowed_networks:
                try:
                    network = ipaddress.ip_network(network_str, strict=False)
                    internal_networks.append(network)
                except ValueError:
                    # Invalid network format, skip
                    if logger:
                        logger.warning(f"Invalid network format in ALLOWED_NETWORKS: {network_str}")
        
        # Check if IP is in any internal network
        for network in internal_networks:
            if remote_ip in network:
                return True
        
        return False
        
    except Exception as e:
        # Log error but fail securely (deny access)
        if logger:
            logger.error(f"Error validating internal request: {e}")
        return False

