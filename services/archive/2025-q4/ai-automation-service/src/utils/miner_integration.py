"""
Miner Integration Client

Provides integration with the automation-miner service for blueprint searches.
This module was recreated to fix the missing import error.

Epic AI-22 Story AI22.1: Automation miner integration maintained for blueprint discovery
"""

import logging
import os
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class MinerIntegration:
    """
    Client for interacting with the automation-miner service.
    
    Provides methods to search blueprints and check service availability.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 10.0
    ):
        """
        Initialize MinerIntegration client.
        
        Args:
            base_url: Base URL for automation-miner service
                     (default: from AUTOMATION_MINER_URL env var or http://automation-miner:8019)
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or 
                        os.getenv("AUTOMATION_MINER_URL") or 
                        "http://automation-miner:8019").rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"}
        )
        logger.info(f"Initialized MinerIntegration client for {self.base_url}")

    async def is_available(self) -> bool:
        """
        Check if automation-miner service is available.
        
        Returns:
            True if service is available, False otherwise
        """
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Automation-miner service unavailable: {e}")
            return False

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def search_blueprints(
        self,
        device: str | None = None,
        min_quality: float = 0.7,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Search for blueprints matching criteria.
        
        Args:
            device: Device type/domain to search for (e.g., 'light', 'switch')
            min_quality: Minimum blueprint quality score (0.0-1.0)
            limit: Maximum number of blueprints to return
            
        Returns:
            List of blueprint dictionaries
        """
        try:
            # Check if service is available first
            if not await self.is_available():
                logger.warning("Automation-miner service unavailable, returning empty results")
                return []

            # Build query parameters
            params: dict[str, Any] = {
                "min_quality": min_quality,
                "limit": limit
            }
            if device:
                params["device"] = device

            # Make request to automation-miner API
            # Try /api/v1/blueprints/search or /blueprints/search
            endpoints = [
                "/api/v1/blueprints/search",
                "/blueprints/search",
                "/api/blueprints/search"
            ]
            
            for endpoint in endpoints:
                try:
                    response = await self.client.get(endpoint, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        # Handle different response formats
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict):
                            # Check for common response wrapper keys
                            return data.get("blueprints", data.get("results", data.get("data", [])))
                        return []
                except httpx.HTTPStatusError:
                    continue
                except Exception as e:
                    logger.debug(f"Error trying endpoint {endpoint}: {e}")
                    continue

            # If all endpoints failed, return empty list
            logger.warning(f"No valid endpoint found for blueprint search in automation-miner")
            return []

        except Exception as e:
            logger.error(f"Error searching blueprints: {e}", exc_info=True)
            return []

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


def get_miner_integration(base_url: str | None = None) -> MinerIntegration:
    """
    Factory function to get MinerIntegration instance.
    
    Args:
        base_url: Optional base URL for automation-miner service
        
    Returns:
        MinerIntegration instance
    """
    return MinerIntegration(base_url=base_url)

