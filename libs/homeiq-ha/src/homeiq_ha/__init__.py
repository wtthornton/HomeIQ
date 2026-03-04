"""HomeIQ Home Assistant integration utilities.

Provides shared Home Assistant connection management and deployment
validation for all HomeIQ services that interact with HA:

- **HAConnectionManager**: WebSocket connection with primary/Nabu Casa fallback
- **Deployment Validation**: Mode-based service startup guards
"""

__version__: str = "1.0.0"

from .deployment_validation import (
    DEPLOYMENT_MODE_PRODUCTION,
    DEPLOYMENT_MODE_TEST,
    check_data_generation_allowed,
    check_test_service_allowed,
    get_deployment_mode,
    get_health_check_info,
    log_deployment_info,
    validate_deployment_mode,
)

__all__: list[str] = [
    "DEPLOYMENT_MODE_PRODUCTION",
    "DEPLOYMENT_MODE_TEST",
    "check_data_generation_allowed",
    "check_test_service_allowed",
    "get_deployment_mode",
    "get_health_check_info",
    "log_deployment_info",
    "validate_deployment_mode",
]
