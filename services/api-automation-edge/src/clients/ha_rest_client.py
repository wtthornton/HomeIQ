"""
Home Assistant REST API Client

Epic A1: REST client with Bearer auth, logging, timeout, retry
"""

import logging
import re
from typing import Any, Dict, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import settings

logger = logging.getLogger(__name__)


class HARestClient:
    """
    Async REST client for Home Assistant API.
    
    Features:
    - Bearer token authentication
    - Request/response logging with secret redaction
    - Timeout + retry (transient errors only)
    - Connection pooling
    """
    
    def __init__(
        self,
        ha_url: Optional[str] = None,
        access_token: Optional[str] = None,
        max_retries: int = 3,
        timeout: float = 10.0
    ):
        """
        Initialize HA REST client.
        
        Args:
            ha_url: Home Assistant URL (defaults to settings)
            access_token: Long-lived access token (defaults to settings)
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
        """
        self.ha_url = (ha_url or settings.ha_http_url or settings.ha_url or "").rstrip('/')
        self.access_token = access_token or settings.ha_token or ""
        self.max_retries = max_retries
        self.timeout = timeout
        
        if not self.ha_url or not self.access_token:
            logger.warning("Home Assistant URL or token not configured")
        
        # Convert WebSocket URL to HTTP if needed
        if self.ha_url.startswith('ws://'):
            self.ha_url = self.ha_url.replace('ws://', 'http://')
        elif self.ha_url.startswith('wss://'):
            self.ha_url = self.ha_url.replace('wss://', 'https://')
        
        # Remove /api/websocket suffix if present
        if self.ha_url.endswith('/api/websocket'):
            self.ha_url = self.ha_url.replace('/api/websocket', '')
        
        # Create async HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10
            ),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        )
        
        logger.info(f"HA REST client initialized with url={self._redact_url(self.ha_url)}")
    
    def _redact_url(self, url: str) -> str:
        """Redact sensitive parts of URL in logs"""
        # Redact token if present in URL
        return re.sub(r'[?&]token=[^&]*', '[REDACTED]', url)
    
    def _redact_secrets(self, data: Any) -> Any:
        """Recursively redact secrets from data structures"""
        if isinstance(data, dict):
            redacted = {}
            for key, value in data.items():
                if any(secret_key in key.lower() for secret_key in ['token', 'password', 'secret', 'key']):
                    redacted[key] = "[REDACTED]"
                else:
                    redacted[key] = self._redact_secrets(value)
            return redacted
        elif isinstance(data, list):
            return [self._redact_secrets(item) for item in data]
        elif isinstance(data, str):
            # Redact if looks like a token
            if len(data) > 20 and all(c.isalnum() or c in '-_' for c in data):
                return "[REDACTED]"
        return data
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        GET request to HA API.
        
        Args:
            endpoint: API endpoint (e.g., '/api/states')
            **kwargs: Additional httpx request parameters
        
        Returns:
            JSON response as dict
        
        Raises:
            httpx.HTTPError: If request fails
        """
        url = f"{self.ha_url}{endpoint}"
        logger.debug(f"GET {endpoint}")
        
        try:
            response = await self.client.get(url, **kwargs)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"GET {endpoint} response: {self._redact_secrets(data)}")
            return data
        except httpx.HTTPError as e:
            logger.error(f"GET {endpoint} failed: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        POST request to HA API.
        
        Args:
            endpoint: API endpoint (e.g., '/api/services/light/turn_on')
            json_data: JSON payload
            **kwargs: Additional httpx request parameters
        
        Returns:
            JSON response as dict
        
        Raises:
            httpx.HTTPError: If request fails
        """
        url = f"{self.ha_url}{endpoint}"
        logger.debug(f"POST {endpoint} with data: {self._redact_secrets(json_data or {})}")
        
        try:
            response = await self.client.post(url, json=json_data, **kwargs)
            response.raise_for_status()
            
            data = response.json() if response.content else {}
            logger.debug(f"POST {endpoint} response: {self._redact_secrets(data)}")
            return data
        except httpx.HTTPError as e:
            logger.error(f"POST {endpoint} failed: {e}")
            raise
    
    async def get_states(self) -> list[Dict[str, Any]]:
        """Get all states from HA"""
        return await self.get("/api/states")
    
    async def get_state(self, entity_id: str) -> Dict[str, Any]:
        """Get state for specific entity"""
        return await self.get(f"/api/states/{entity_id}")
    
    async def call_service(
        self,
        domain: str,
        service: str,
        service_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Call a Home Assistant service.
        
        Args:
            domain: Service domain (e.g., 'light')
            service: Service name (e.g., 'turn_on')
            service_data: Service data payload
        
        Returns:
            Service call response
        """
        endpoint = f"/api/services/{domain}/{service}"
        return await self.post(endpoint, json_data=service_data)
    
    async def get_services(self) -> Dict[str, Any]:
        """Get available services from HA"""
        return await self.get("/api/services")
    
    async def get_config(self) -> Dict[str, Any]:
        """Get HA configuration"""
        return await self.get("/api/config")
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        logger.info("HA REST client closed")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
