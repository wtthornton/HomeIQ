"""
Shared Error Handlers for API Routes

Epic 39, Story 39.10: Automation Service Foundation
Extracts common error handling patterns to reduce duplication.
"""

import logging
from functools import wraps
from typing import Any, Callable, TypeVar

from fastapi import HTTPException

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def handle_route_errors(
    operation_name: str,
    default_status_code: int = 500
) -> Callable[[F], F]:
    """
    Decorator to handle common route errors.
    
    Args:
        operation_name: Name of the operation for logging (e.g., "deploy suggestion")
        default_status_code: Default HTTP status code for errors (default: 500)
    
    Usage:
        @router.post("/endpoint")
        @handle_route_errors("deploy suggestion")
        async def deploy_suggestion(...):
            result = await service.deploy(...)
            return result
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTP exceptions (e.g., 404, 400) as-is
                raise
            except Exception as e:
                logger.error(f"Failed to {operation_name}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=default_status_code,
                    detail=str(e)
                )
        return wrapper  # type: ignore
    return decorator


def handle_service_errors(
    service_name: str,
    operation: str,
    default_status_code: int = 500
) -> Callable[[F], F]:
    """
    Decorator specifically for service method errors.
    
    Args:
        service_name: Name of the service (e.g., "deployment")
        operation: Name of the operation (e.g., "deploy suggestion")
        default_status_code: Default HTTP status code for errors
    
    Usage:
        @handle_service_errors("deployment", "deploy suggestion")
        async def deploy_suggestion(...):
            ...
    """
    return handle_route_errors(
        operation_name=f"{service_name} {operation}",
        default_status_code=default_status_code
    )

