"""
Patterns API Client

Client for querying automation patterns from AI Automation Service.
"""
import logging
from typing import Any

import aiohttp

from ..config import Settings

logger = logging.getLogger(__name__)


class PatternsClient:
    """Client for querying patterns from AI Automation Service"""

    def __init__(self, base_url: str | None = None, settings: Settings | None = None):
        """
        Initialize patterns client.

        Args:
            base_url: Base URL for AI Automation Service (defaults to config)
            settings: Settings instance (optional, will create if not provided)
        """
        if settings is None:
            settings = Settings()
        self.base_url = (base_url or settings.ai_automation_service_url).rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=10)

    async def get_patterns(
        self,
        pattern_type: str | None = None,
        device_ids: list[str] | None = None,
        min_confidence: float = 0.7,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get patterns from AI Automation Service.

        Args:
            pattern_type: Filter by pattern type (time_of_day, co_occurrence, etc.)
            device_ids: Filter by device IDs
            min_confidence: Minimum confidence threshold
            limit: Maximum number of patterns to return

        Returns:
            List of pattern dictionaries
        """
        try:
            params: dict[str, Any] = {
                "min_confidence": min_confidence,
                "limit": limit
            }
            
            if pattern_type:
                params["pattern_type"] = pattern_type

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{self.base_url}/api/patterns/list",
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        patterns = data.get("data", {}).get("patterns", [])
                        
                        # Filter by device_ids if provided
                        if device_ids:
                            filtered_patterns = []
                            for pattern in patterns:
                                pattern_device_id = pattern.get("device_id") or pattern.get("pattern_metadata", {}).get("device_id")
                                if pattern_device_id in device_ids:
                                    filtered_patterns.append(pattern)
                            patterns = filtered_patterns
                        
                        logger.info(f"Retrieved {len(patterns)} patterns from API")
                        return patterns
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to fetch patterns: {response.status} - {error_text}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching patterns: {e}", exc_info=True)
            return []

