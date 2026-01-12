"""
Synergies API Client

Client for querying automation synergies from AI Automation Service.
"""
import logging
from typing import Any

import aiohttp

from ..config import Settings

logger = logging.getLogger(__name__)


class SynergiesClient:
    """Client for querying synergies from AI Automation Service"""

    def __init__(self, base_url: str | None = None, settings: Settings | None = None):
        """
        Initialize synergies client.

        Args:
            base_url: Base URL for AI Automation Service (defaults to config)
            settings: Settings instance (optional, will create if not provided)
        """
        if settings is None:
            settings = Settings()
        self.base_url = (base_url or settings.ai_automation_service_url).rstrip("/")
        self.api_key = settings.ai_automation_api_key
        self.timeout = aiohttp.ClientTimeout(total=60)  # Increased for larger result sets (5000 limit)

    async def get_synergies(
        self,
        area: str | None = None,
        device_ids: list[str] | None = None,
        min_confidence: float = 0.6,
        limit: int = 5000
    ) -> list[dict[str, Any]]:
        """
        Get synergies from AI Automation Service.

        Args:
            area: Filter by area
            device_ids: Filter by device IDs (checks if devices are in synergy)
            min_confidence: Minimum confidence threshold
            limit: Maximum number of synergies to return (default: 5000)

        Returns:
            List of synergy dictionaries
        """
        try:
            params: dict[str, Any] = {
                "min_confidence": min_confidence,
                "limit": limit
            }
            
            if area:
                params["area"] = area

            headers = {}
            if self.api_key:
                headers["X-HomeIQ-API-Key"] = self.api_key
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{self.base_url}/api/synergies",
                    params=params,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        synergies = data.get("data", {}).get("synergies", [])
                        
                        # Filter by device_ids if provided
                        if device_ids:
                            filtered_synergies = []
                            for synergy in synergies:
                                synergy_device_ids = synergy.get("device_ids", [])
                                # Check if any device_ids overlap
                                if any(did in synergy_device_ids for did in device_ids):
                                    filtered_synergies.append(synergy)
                            synergies = filtered_synergies
                        
                        logger.info(f"Retrieved {len(synergies)} synergies from API")
                        return synergies
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to fetch synergies: {response.status} - {error_text}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching synergies: {e}", exc_info=True)
            return []

