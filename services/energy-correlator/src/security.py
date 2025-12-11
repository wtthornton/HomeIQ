"""
Security Validation Utilities
Epic 48 Story 48.1: Security Hardening & Input Validation

Provides validation functions for API endpoints and bucket names.
"""

import ipaddress
import re
from typing import Optional

from aiohttp import web


def validate_bucket_name(bucket: str) -> str:
    """
    Validate InfluxDB bucket name format.
    
    Args:
        bucket: The bucket name to validate
        
    Returns:
        Validated bucket name
        
    Raises:
        ValueError: If bucket name is invalid
    """
    if not bucket:
        raise ValueError("Bucket name cannot be empty")
    
    # Check length (InfluxDB limit is typically 255 characters)
    if len(bucket) > 255:
        raise ValueError(
            f"Invalid bucket name: '{bucket}' exceeds maximum length of 255 characters."
        )
    
    # InfluxDB bucket names: alphanumeric, hyphens, underscores only
    if not re.match(r'^[a-zA-Z0-9_-]+$', bucket):
        raise ValueError(
            f"Invalid bucket name format: '{bucket}'. "
            "Bucket names must contain only alphanumeric characters, hyphens, and underscores."
        )
    
    return bucket


def validate_internal_request(request: web.Request, allowed_networks: Optional[list[str]] = None) -> bool:
    """
    Validate if a request originates from an allowed internal network.
    
    Args:
        request: The aiohttp request object
        allowed_networks: List of allowed CIDR networks (e.g., ['172.16.0.0/12', '192.168.0.0/16'])
                         If provided, these networks are used. If None, defaults to internal ranges.
        
    Returns:
        True if the request is from an allowed internal network,
        False otherwise.
    """
    # Default to common internal network ranges if not specified
    default_networks = ['127.0.0.1/32', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']
    
    if allowed_networks is None:
        allowed_networks = default_networks
    else:
        # Combine custom networks with defaults
        allowed_networks = list(set(allowed_networks + default_networks))
    
    peername = request.remote
    if not peername:
        return False
    
    # Extract IP from "IP:PORT" format if present
    if ':' in peername:
        peername = peername.split(':')[0]
    
    try:
        request_ip = ipaddress.ip_address(peername)
        for network_str in allowed_networks:
            try:
                network = ipaddress.ip_network(network_str, strict=False)
                if request_ip in network:
                    return True
            except ValueError:
                # Skip invalid network formats
                continue
        return False
    except ValueError:
        return False


async def require_internal_network(request: web.Request, allowed_networks: Optional[list[str]] = None) -> None:
    """
    Middleware function to require requests from internal networks.
    
    Args:
        request: The aiohttp request object
        allowed_networks: List of allowed CIDR networks
        
    Raises:
        web.HTTPForbidden: If request is not from allowed network
    """
    if not validate_internal_request(request, allowed_networks):
        raise web.HTTPForbidden(
            text="Access denied. This endpoint is only accessible from internal networks."
        )
