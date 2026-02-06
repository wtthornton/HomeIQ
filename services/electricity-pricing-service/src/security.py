"""
Security Validation Utilities
Epic 49 Story 49.1: Security Hardening & Input Validation

Provides validation functions for API endpoints and input parameters.
"""

import ipaddress
import logging
from typing import Optional

from aiohttp import web

logger = logging.getLogger(__name__)


def validate_hours_parameter(hours_str: str | None, default: int = 4) -> int:
    """
    Validate and parse hours parameter for cheapest-hours endpoint.
    
    Args:
        hours_str: The hours parameter from query string
        default: Default value if parameter is missing
        
    Returns:
        Validated hours value (1-24)
        
    Raises:
        ValueError: If hours parameter is invalid with clear error message
    """
    if hours_str is None:
        return default
    
    try:
        hours = int(hours_str)
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid hours parameter: '{hours_str}'. "
            "Hours must be an integer between 1 and 24."
        )
    
    if hours < 1 or hours > 24:
        raise ValueError(
            f"Hours parameter out of range: {hours}. "
            "Hours must be between 1 and 24."
        )
    
    return hours


def validate_internal_request(request: web.Request, allowed_networks: Optional[list[str]]) -> bool:
    """
    Validate if a request originates from an allowed internal network.
    
    Args:
        request: The aiohttp request object
        allowed_networks: List of allowed CIDR networks (e.g., ['172.16.0.0/12'])
        
    Returns:
        True if the request is from an allowed internal network or if no networks are specified,
        False otherwise.
    """
    if not allowed_networks:
        # If no allowed networks are configured, all requests are considered internal
        return True

    peername = request.remote
    if not peername:
        logger.warning("Could not determine remote address for internal request validation.")
        return False

    try:
        request_ip = ipaddress.ip_address(peername)
        for network_str in allowed_networks:
            network = ipaddress.ip_network(network_str)
            if request_ip in network:
                return True

        logger.warning(f"Request from {request_ip} rejected: not in allowed networks")
        return False
    except ValueError as e:
        logger.error(f"Invalid IP address or network configuration for validation: {e}")
        return False


async def require_internal_network(request: web.Request, allowed_networks: Optional[list[str]]) -> None:
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

