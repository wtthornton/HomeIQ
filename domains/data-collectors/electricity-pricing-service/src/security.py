"""Security Validation Utilities.

Epic 49 Story 49.1: Security Hardening & Input Validation

Provides validation functions for API endpoints and input parameters.
"""

import ipaddress
import logging

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


def validate_hours_parameter(hours_str: str | None, default: int = 4) -> int:
    """Validate and parse hours parameter for cheapest-hours endpoint.

    Args:
        hours_str: The hours parameter from query string.
        default: Default value if parameter is missing.

    Returns:
        Validated hours value (1-24).

    Raises:
        ValueError: If hours parameter is invalid with clear error message.
    """
    if hours_str is None:
        return default

    try:
        hours = int(hours_str)
    except (ValueError, TypeError) as err:
        msg = (
            f"Invalid hours parameter: '{hours_str}'. "
            "Hours must be an integer between 1 and 24."
        )
        raise ValueError(msg) from err

    if hours < 1 or hours > 24:
        msg = f"Hours parameter out of range: {hours}. Hours must be between 1 and 24."
        raise ValueError(msg)

    return hours


def validate_internal_request(request: Request, allowed_networks: list[str] | None) -> bool:
    """Validate if a request originates from an allowed internal network.

    Args:
        request: The FastAPI request object.
        allowed_networks: List of allowed CIDR networks (e.g., ['172.16.0.0/12']).

    Returns:
        True if the request is from an allowed internal network or if no networks are specified,
        False otherwise.
    """
    if not allowed_networks:
        return True

    peername = request.client.host if request.client else None
    if not peername:
        logger.warning("Could not determine remote address for internal request validation.")
        return False

    try:
        request_ip = ipaddress.ip_address(peername)
        for network_str in allowed_networks:
            network = ipaddress.ip_network(network_str)
            if request_ip in network:
                return True

        logger.warning("Request from %s rejected: not in allowed networks", request_ip)
        return False
    except ValueError as e:
        logger.error("Invalid IP address or network configuration for validation: %s", e)
        return False


def require_internal_network(request: Request, allowed_networks: list[str] | None) -> None:
    """Require requests from internal networks.

    Args:
        request: The FastAPI request object.
        allowed_networks: List of allowed CIDR networks.

    Raises:
        HTTPException: If request is not from allowed network.
    """
    if not validate_internal_request(request, allowed_networks):
        raise HTTPException(
            status_code=403,
            detail="Access denied. This endpoint is only accessible from internal networks.",
        )
