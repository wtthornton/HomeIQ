"""
Epic 40: Deployment Mode Validation
Validates deployment configuration and prevents misconfigurations.
"""

import logging
import os
import sys
from typing import Literal

logger = logging.getLogger(__name__)

# Deployment modes
DEPLOYMENT_MODE_TEST = "test"
DEPLOYMENT_MODE_PRODUCTION = "production"

# Service types
SERVICE_TYPE_DATA_GENERATION = "data_generation"
SERVICE_TYPE_EXTERNAL_API = "external_api"
SERVICE_TYPE_AI = "ai"
SERVICE_TYPE_CORE = "core"
SERVICE_TYPE_TEST = "test"


def get_deployment_mode() -> str:
    """Get current deployment mode from environment variable."""
    return os.getenv("DEPLOYMENT_MODE", DEPLOYMENT_MODE_PRODUCTION).lower()


def validate_deployment_mode(
    service_name: str,
    service_type: str,
    allowed_modes: list[str] | None = None,
) -> bool:
    """
    Validate that service can run in current deployment mode.
    
    Args:
        service_name: Name of the service for logging
        service_type: Type of service (data_generation, external_api, ai, core, test)
        allowed_modes: List of allowed deployment modes (default based on service_type)
    
    Returns:
        True if service can run, False otherwise
    
    Raises:
        SystemExit: If service cannot run in current mode (with error message)
    """
    deployment_mode = get_deployment_mode()
    
    # Default allowed modes based on service type
    if allowed_modes is None:
        if service_type == SERVICE_TYPE_DATA_GENERATION:
            allowed_modes = [DEPLOYMENT_MODE_TEST]
        elif service_type == SERVICE_TYPE_EXTERNAL_API:
            allowed_modes = [DEPLOYMENT_MODE_PRODUCTION]
        elif service_type == SERVICE_TYPE_TEST:
            allowed_modes = [DEPLOYMENT_MODE_TEST]
        else:  # AI, Core services
            allowed_modes = [DEPLOYMENT_MODE_TEST, DEPLOYMENT_MODE_PRODUCTION]
    
    if deployment_mode not in allowed_modes:
        error_msg = (
            f"❌ {service_name} cannot run in {deployment_mode} mode. "
            f"Allowed modes: {', '.join(allowed_modes)}"
        )
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    
    logger.info(f"✅ {service_name} validated for {deployment_mode} mode")
    return True


def check_data_generation_allowed(service_name: str) -> bool:
    """
    Check if data generation services are allowed in current deployment mode.
    Data generation services should only run in test mode.
    
    Args:
        service_name: Name of the service for logging
    
    Returns:
        True if allowed, False otherwise
    
    Raises:
        SystemExit: If not allowed (production mode)
    """
    return validate_deployment_mode(
        service_name=service_name,
        service_type=SERVICE_TYPE_DATA_GENERATION,
    )


def check_test_service_allowed(service_name: str) -> bool:
    """
    Check if test services are allowed in current deployment mode.
    Test services should only run in test mode.
    
    Args:
        service_name: Name of the service for logging
    
    Returns:
        True if allowed, False otherwise
    
    Raises:
        SystemExit: If not allowed (production mode)
    """
    return validate_deployment_mode(
        service_name=service_name,
        service_type=SERVICE_TYPE_TEST,
    )


def log_deployment_info(service_name: str) -> None:
    """Log deployment mode information on service startup."""
    deployment_mode = get_deployment_mode()
    logger.info(f"🚀 {service_name} starting in {deployment_mode} mode")
    logger.info(f"   Deployment Mode: {deployment_mode}")
    logger.info(f"   Service Name: {service_name}")


def get_health_check_info() -> dict:
    """Get deployment mode information for health checks."""
    return {
        "deployment_mode": get_deployment_mode(),
        "is_test": get_deployment_mode() == DEPLOYMENT_MODE_TEST,
        "is_production": get_deployment_mode() == DEPLOYMENT_MODE_PRODUCTION,
    }

