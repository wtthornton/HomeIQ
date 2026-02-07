"""
Device Context Classifier
Phase 2.1: Core classification logic
"""

import asyncio
import logging
import os
from typing import Any

import aiohttp

from .patterns import get_device_category, match_device_pattern

logger = logging.getLogger("device-context-classifier")


class DeviceContextClassifier:
    """Classifies devices based on entity patterns."""

    def __init__(self):
        """Initialize classifier."""
        self.ha_url = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
        self.ha_token = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
        self._session: aiohttp.ClientSession | None = None

        # Validate token at construction
        if not self.ha_token:
            logger.warning("HA_TOKEN not configured - classifier will not be able to query Home Assistant")
        if not self.ha_url:
            logger.warning("HA_URL not configured - classifier will not be able to query Home Assistant")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HA API session."""
        if self._session is None or self._session.closed:
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
                raise_for_status=False
            )
        return self._session

    async def _fetch_entity_state(
        self,
        session: aiohttp.ClientSession,
        entity_id: str
    ) -> dict[str, Any] | None:
        """Fetch a single entity's state from HA. Returns state data or None on failure."""
        state_url = f"{self.ha_url}/api/states/{entity_id}"
        try:
            async with session.get(state_url) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    logger.warning("HA API returned 401 Unauthorized for %s - check HA_TOKEN", entity_id)
                elif response.status == 404:
                    logger.debug("Entity %s not found in HA (404)", entity_id)
                else:
                    logger.warning("Failed to fetch state for %s: HTTP %d", entity_id, response.status)
        except Exception as e:
            logger.error("Error fetching state for %s: %s", entity_id, e)
        return None

    async def classify_device(
        self,
        device_id: str,
        entity_ids: list[str]
    ) -> dict[str, Any]:
        """
        Classify a device based on its entities.

        Args:
            device_id: Device identifier
            entity_ids: List of entity IDs for this device

        Returns:
            Classification result with device_type, device_category, and confidence
        """
        if not self.ha_url or not self.ha_token:
            logger.warning("HA_URL or HA_TOKEN not configured")
            return {
                "device_id": device_id,
                "device_type": None,
                "device_category": None,
                "confidence": 0.0,
                "matched_entities": 0
            }

        try:
            session = await self._get_session()

            # Get entity registry
            registry_url = f"{self.ha_url}/api/config/entity_registry/list"
            async with session.get(registry_url) as response:
                if response.status != 200:
                    logger.warning("Failed to get entity registry: HTTP %d", response.status)
                    return {
                        "device_id": device_id,
                        "device_type": None,
                        "device_category": None,
                        "confidence": 0.0,
                        "matched_entities": 0
                    }

                # FIX: HA returns a flat list, not {"entities": [...]}
                registry_data = await response.json()
                entities = registry_data if isinstance(registry_data, list) else registry_data.get("entities", [])

            # FIX: Extract domains unconditionally (not gated behind registry lookup)
            entity_domains = []
            for entity_id in entity_ids:
                domain = entity_id.split(".")[0] if "." in entity_id else None
                if domain:
                    entity_domains.append(domain)

            # FIX: Use asyncio.gather() for concurrent entity state fetches (not N+1 sequential)
            state_tasks = [
                self._fetch_entity_state(session, entity_id)
                for entity_id in entity_ids
            ]
            state_results = await asyncio.gather(*state_tasks)

            # FIX: Collect unique attribute keys instead of merging dicts (avoids overwrites)
            entity_attribute_keys: set[str] = set()
            for state_data in state_results:
                if state_data is not None:
                    attrs = state_data.get("attributes", {})
                    entity_attribute_keys.update(attrs.keys())

            # Match pattern - now returns (device_type, confidence) tuple
            device_type, confidence = match_device_pattern(entity_domains, entity_attribute_keys)
            device_category = get_device_category(device_type)

            return {
                "device_id": device_id,
                "device_type": device_type,
                "device_category": device_category,
                "confidence": confidence,
                "matched_entities": len(entity_ids)
            }

        except Exception as e:
            logger.error("Error classifying device %s: %s", device_id, e)
            return {
                "device_id": device_id,
                "device_type": None,
                "device_category": None,
                "confidence": 0.0,
                "matched_entities": 0
            }

    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
