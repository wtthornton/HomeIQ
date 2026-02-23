"""
Shared Service-to-Service HTTP Client

Epic 39, Story 39.11: Shared Infrastructure Setup
HTTP client utilities for inter-service communication.
"""

import logging
from typing import Optional, Any
from datetime import datetime, timedelta

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .logging_config import get_logger

logger = get_logger(__name__)


class ServiceClient:
    """
    HTTP client for service-to-service communication.
    
    Features:
    - Automatic retry with exponential backoff
    - Request timeout handling
    - Error handling and logging
    - Health check support
    """
    
    def __init__(
        self,
        service_name: str,
        base_url: str,
        timeout: float = 5.0,
        max_retries: int = 3
    ):
        """
        Initialize service client.
        
        Args:
            service_name: Name of the service (for logging)
            base_url: Base URL of the service (e.g., "http://data-api:8006")
            timeout: Request timeout in seconds (default: 5.0)
            max_retries: Maximum retry attempts (default: 3)
        """
        self.service_name = service_name
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            follow_redirects=True
        )
        
        logger.info(f"ServiceClient initialized: {service_name} at {base_url}")
    
    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def get(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None
    ) -> dict[str, Any]:
        """
        Send GET request to service.
        
        Args:
            path: API path (e.g., "/api/v1/health")
            params: Query parameters
            headers: Optional headers
        
        Returns:
            Response JSON as dictionary
        
        Raises:
            httpx.HTTPStatusError: If request fails after retries
        """
        try:
            response = await self.client.get(
                path,
                params=params,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"GET {self.service_name}{path} failed: {e}")
            raise
    
    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def post(
        self,
        path: str,
        data: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None
    ) -> dict[str, Any]:
        """
        Send POST request to service.
        
        Args:
            path: API path
            data: Form data
            json: JSON data
            headers: Optional headers
        
        Returns:
            Response JSON as dictionary
        """
        try:
            response = await self.client.post(
                path,
                data=data,
                json=json,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"POST {self.service_name}{path} failed: {e}")
            raise
    
    async def health_check(self) -> dict[str, Any]:
        """
        Check service health.
        
        Returns:
            Health status dictionary
        
        Raises:
            httpx.RequestError: If health check fails
        """
        try:
            return await self.get("/health")
        except Exception as e:
            logger.warning(f"Health check failed for {self.service_name}: {e}")
            raise
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        logger.debug(f"ServiceClient closed: {self.service_name}")


# Pre-configured service clients (can be extended)
_service_clients: dict[str, ServiceClient] = {}


def get_service_client(
    service_name: str,
    base_url: Optional[str] = None,
    timeout: float = 5.0
) -> ServiceClient:
    """
    Get or create a service client (singleton pattern).
    
    Args:
        service_name: Name of the service
        base_url: Optional base URL (if not provided, uses default)
        timeout: Request timeout
    
    Returns:
        ServiceClient instance
    
    Example:
        ```python
        from shared.service_client import get_service_client
        
        client = get_service_client(
            "data-api",
            base_url="http://data-api:8006"
        )
        
        data = await client.get("/api/v1/events")
        ```
    """
    if service_name not in _service_clients:
        if base_url is None:
            # Use default service URLs based on service name
            defaults = {
                "data-api": "http://data-api:8006",
                "ai-query-service": "http://ai-query-service:8018",
                "ai-automation-service": "http://ai-automation-service:8021",
                "ai-training-service": "http://ai-training-service:8015",
                "ai-pattern-service": "http://ai-pattern-service:8016",
            }
            base_url = defaults.get(service_name)
            
            if base_url is None:
                raise ValueError(f"No default URL for service: {service_name}")
        
        _service_clients[service_name] = ServiceClient(
            service_name=service_name,
            base_url=base_url,
            timeout=timeout
        )
    
    return _service_clients[service_name]


async def close_all_clients():
    """Close all service clients (for cleanup)"""
    global _service_clients
    
    for client in _service_clients.values():
        await client.close()
    
    _service_clients.clear()
    logger.info("All service clients closed")

