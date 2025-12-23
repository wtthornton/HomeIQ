"""
Home Assistant API Client (2025 Patterns)

Epic 39, Story 39.10: Automation Service Foundation
Async client for deploying and managing automations in Home Assistant.
"""

import logging
import uuid
from typing import Any

import httpx
import yaml
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import settings

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """
    Async client for interacting with Home Assistant REST API.
    
    Features:
    - Async HTTP requests with httpx
    - Automatic retry logic
    - Connection pooling
    - Proper error handling
    """

    def __init__(
        self,
        ha_url: str | None = None,
        access_token: str | None = None,
        max_retries: int = 3,
        timeout: float = 10.0
    ):
        """
        Initialize HA client.
        
        Args:
            ha_url: Home Assistant URL (defaults to settings.ha_url)
            access_token: Long-lived access token (defaults to settings.ha_token)
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
        """
        self.ha_url = (ha_url or settings.ha_url or "").rstrip('/')
        self.access_token = access_token or settings.ha_token or ""
        self.max_retries = max_retries
        self.timeout = timeout
        
        if not self.ha_url or not self.access_token:
            logger.warning("Home Assistant URL or token not configured")
        
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
        
        logger.info(f"Home Assistant client initialized with url={self.ha_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def deploy_automation(self, automation_yaml: str) -> dict[str, Any]:
        """
        Deploy automation to Home Assistant.
        
        Args:
            automation_yaml: Home Assistant automation YAML as string
        
        Returns:
            Dictionary with automation_id and status
        
        Raises:
            httpx.HTTPError: If deployment fails
            ValueError: If YAML is invalid
        """
        if not self.ha_url or not self.access_token:
            raise ValueError("Home Assistant URL and token must be configured")
        
        # Parse YAML to validate
        try:
            automation_data = yaml.safe_load(automation_yaml)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
        
        # Generate unique automation ID if not present
        if "id" not in automation_data:
            automation_data["id"] = f"automation.{uuid.uuid4().hex[:8]}"
        
        automation_id = automation_data["id"]
        
        # Deploy via Home Assistant API
        url = f"{self.ha_url}/api/config/automation/config/{automation_id}"
        
        try:
            response = await self.client.post(
                url,
                json=automation_data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ Automation deployed: {automation_id}")
            return {
                "automation_id": automation_id,
                "status": "deployed",
                "data": result
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to deploy automation: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error deploying automation: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def get_automation(self, automation_id: str) -> dict[str, Any] | None:
        """
        Get automation from Home Assistant.
        
        Args:
            automation_id: Automation entity ID
        
        Returns:
            Automation data or None if not found
        """
        if not self.ha_url or not self.access_token:
            return None
        
        url = f"{self.ha_url}/api/config/automation/config/{automation_id}"
        
        try:
            response = await self.client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get automation {automation_id}: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def list_automations(self) -> list[dict[str, Any]]:
        """
        List all automations from Home Assistant.
        
        Returns:
            List of automation dictionaries
        """
        if not self.ha_url or not self.access_token:
            return []
        
        url = f"{self.ha_url}/api/config/automation/config"
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
        except httpx.HTTPError as e:
            logger.error(f"Failed to list automations: {e}")
            return []

    async def enable_automation(self, automation_id: str) -> bool:
        """
        Enable an automation.
        
        Args:
            automation_id: Automation entity ID
        
        Returns:
            True if successful
        """
        if not self.ha_url or not self.access_token:
            return False
        
        url = f"{self.ha_url}/api/services/automation/turn_on"
        
        try:
            response = await self.client.post(
                url,
                json={"entity_id": automation_id}
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to enable automation {automation_id}: {e}")
            return False

    async def disable_automation(self, automation_id: str) -> bool:
        """
        Disable an automation.
        
        Args:
            automation_id: Automation entity ID
        
        Returns:
            True if successful
        """
        if not self.ha_url or not self.access_token:
            return False
        
        url = f"{self.ha_url}/api/services/automation/turn_off"
        
        try:
            response = await self.client.post(
                url,
                json={"entity_id": automation_id}
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to disable automation {automation_id}: {e}")
            return False

    async def health_check(self) -> bool:
        """
        Check if Home Assistant is accessible.
        
        Returns:
            True if service is healthy
        """
        if not self.ha_url or not self.access_token:
            return False
        
        try:
            url = f"{self.ha_url}/api/"
            response = await self.client.get(url, timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Home Assistant health check failed: {e}")
            return False

    async def close(self):
        """Close HTTP client connection."""
        await self.client.aclose()
        logger.debug("Home Assistant client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

