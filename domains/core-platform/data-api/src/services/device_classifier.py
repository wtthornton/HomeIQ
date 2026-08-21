"""Device classification.

`device_type` is a decision input — it filters `GET /api/devices` and drives the
"similar devices" recommender — so every rule here must survive a rename. Entity
domains and manufacturer/model are platform- and vendor-assigned and do; a
friendly name is not, and is never read. See `.claude/rules/friendly-names.md`.
"""

import logging
import os
import re
from typing import Any

import aiohttp
from homeiq_device_taxonomy import get_device_category, match_device_pattern

logger = logging.getLogger(__name__)

# The taxonomy import is deliberately unguarded. It used to sit behind a
# `try/except ImportError` that appended a relative path to `sys.path` and fell
# back to stubs returning None. The path resolved to a directory that has never
# existed, so the stubs were always live: every device with entities classified
# as None, and the only rule that ever assigned a device_type was a keyword scan
# over the device's name. A missing vocabulary must break the build, not degrade
# into silence (TAP-6392).


class DeviceClassifierService:
    """Service for classifying devices"""

    def __init__(self):
        """Initialize classifier service"""
        self.ha_url = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
        self.ha_token = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HA API session"""
        if self._session is None or self._session.closed:
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json",
            }
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(
                headers=headers, timeout=timeout, raise_for_status=False
            )
        return self._session

    async def classify_device(self, device_id: str, entity_ids: list[str]) -> dict[str, Any]:
        """
        Classify a device based on its entities (legacy method - extracts domains from entity_ids).

        Args:
            device_id: Device identifier
            entity_ids: List of entity IDs for this device (e.g., ["light.kitchen", "sensor.temp"])

        Returns:
            Classification result with device_type and device_category
        """
        # Extract entity domains from entity IDs
        entity_domains = []
        for entity_id in entity_ids:
            if "." in entity_id:
                domain = entity_id.split(".")[0]
                entity_domains.append(domain)

        return await self.classify_device_from_domains(device_id, entity_domains, entity_ids)

    async def classify_device_from_domains(
        self,
        device_id: str,
        entity_domains: list[str],
        entity_ids: list[str] | None = None,  # noqa: ARG002
    ) -> dict[str, Any]:
        """
        Classify a device based on entity domains.

        Uses domain-based classification (primary) with pattern matching (fallback).
        No HA API calls needed - uses entity domains directly.

        Args:
            device_id: Device identifier
            entity_domains: List of entity domains (e.g., ["light", "sensor"])
            entity_ids: Optional list of entity IDs for logging/debugging

        Returns:
            Classification result with device_type and device_category
        """
        try:
            if not entity_domains:
                return {"device_id": device_id, "device_type": None, "device_category": None}

            # PRIMARY: domain-based classification. match_device_pattern returns
            # (device_type, confidence) — binding the tuple to device_type would
            # write "('light', 0.95)" into the column (TAP-6392).
            device_type, _confidence = match_device_pattern(entity_domains, set())
            device_category = get_device_category(device_type)

            return {
                "device_id": device_id,
                "device_type": device_type,
                "device_category": device_category,
            }

        except Exception as e:
            logger.error(f"Error classifying device {device_id}: {e}")
            return {"device_id": device_id, "device_type": None, "device_category": None}

    # Ordered model-keyword rules, most specific first. Applied only when a
    # device exposes no entities, so the durable domain-based path cannot run.
    _MODEL_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("light", ("downlight", "lightstrip", "light strip", "bulb", "lamp", "led", "light")),
        ("media_player", ("television", "soundbar", "tv")),
        ("switch", ("outlet", "smart plug", "smartplug", "switch")),
        ("sensor", ("motion", "presence", "temperature", "humidity", "sensor")),
        ("vacuum", ("roborock", "vacuum")),
        ("thermostat", ("thermostat", "hvac", "climate")),
        ("lock", ("deadbolt", "lock")),
        ("camera", ("camera",)),
        ("fan", ("fan",)),
        ("button", ("button", "remote")),
    )

    def classify_device_by_metadata(
        self, device_id: str, model: str | None = None
    ) -> dict[str, Any]:
        """Classify a device from its model string, for devices that expose no entities.

        Last resort. A device with entities is classified by
        :meth:`classify_device_from_domains`, which is both more accurate and
        genuinely structural; this runs only when there are no entities at all.

        Matching is on **model** alone, deliberately.

        - The device *name* is excluded because a rename would change the answer,
          which the friendly-names rule forbids for a decision input.
        - The *manufacturer* is excluded because it names a vendor, not a device
          type, and on this instance that distinction is not academic: the four
          entity-less devices include two Hue **Room** groups whose manufacturer
          is "Signify Netherlands B.V.". Matching the brand token "signify"
          classified both as lights. A room is not a light. Manufacturer is
          rename-proof but it is not evidence of what a device *is* (TAP-6392).

        Keywords match on word boundaries, so "flight" does not contain "light"
        and "Netvue" does not contain "tv".

        Returns `device_type: None` when the model carries no signal, rather
        than guessing.
        """
        try:
            if not model:
                return {"device_id": device_id, "device_type": None, "device_category": None}

            haystack = model.lower()
            for device_type, keywords in self._MODEL_KEYWORDS:
                if any(re.search(rf"\b{re.escape(kw)}\b", haystack) for kw in keywords):
                    return {
                        "device_id": device_id,
                        "device_type": device_type,
                        "device_category": get_device_category(device_type),
                    }

            return {"device_id": device_id, "device_type": None, "device_category": None}

        except Exception as e:
            logger.error(f"Error classifying device {device_id} by metadata: {e}")
            return {"device_id": device_id, "device_type": None, "device_category": None}


# Singleton instance
_classifier_service: DeviceClassifierService | None = None


def get_classifier_service() -> DeviceClassifierService:
    """Get singleton classifier service instance"""
    global _classifier_service
    if _classifier_service is None:
        _classifier_service = DeviceClassifierService()
    return _classifier_service
