"""
Device Classification Service
Phase 2.1: Classify devices based on entity patterns
"""

import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Import patterns from device-context-classifier
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '../../../device-context-classifier/src'))
    from patterns import get_device_category, match_device_pattern
except ImportError:
    # Fallback if classifier service not available
    logger.warning("Device context classifier patterns not available, using fallback")
    def match_device_pattern(entity_domains, entity_attributes):
        return None
    def get_device_category(device_type):
        return None


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
                "Content-Type": "application/json"
            }
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
                raise_for_status=False
            )
        return self._session

    async def classify_device(
        self,
        device_id: str,
        entity_ids: list[str]
    ) -> dict[str, Any]:
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
        entity_ids: list[str] | None = None
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
                return {
                    "device_id": device_id,
                    "device_type": None,
                    "device_category": None
                }
            
            # PRIMARY: Domain-based classification (no HA API needed)
            # Use improved match_device_pattern which uses domain mapping first
            device_type = match_device_pattern(entity_domains, {})
            device_category = get_device_category(device_type)
            
            return {
                "device_id": device_id,
                "device_type": device_type,
                "device_category": device_category
            }
            
        except Exception as e:
            logger.error(f"Error classifying device {device_id}: {e}")
            return {
                "device_id": device_id,
                "device_type": None,
                "device_category": None
            }
    
    def classify_device_by_metadata(
        self,
        device_id: str,
        name: str,
        manufacturer: str | None = None,
        model: str | None = None
    ) -> dict[str, Any]:
        """
        Classify device by name/manufacturer/model patterns (fallback when entities unavailable).
        
        Uses device metadata to infer device type when entity domains aren't available.
        
        Args:
            device_id: Device identifier
            name: Device name
            manufacturer: Device manufacturer (optional)
            model: Device model (optional)
            
        Returns:
            Classification result with device_type and device_category
        """
        try:
            name_lower = name.lower() if name else ""
            manufacturer_lower = manufacturer.lower() if manufacturer else ""
            model_lower = model.lower() if model else ""
            combined = f"{name_lower} {manufacturer_lower} {model_lower}".strip()
            
            # Pattern matching on device name/manufacturer/model
            # Check patterns in priority order (most specific first)
            
            # Lights (check first - many devices have "light" in name)
            if any(keyword in combined for keyword in ["hue", "downlight", "lightstrip", "light strip", "lightstrip", "bulb", "lamp", "led", "signify"]):
                return {
                    "device_id": device_id,
                    "device_type": "light",
                    "device_category": "lighting"
                }
            elif "light" in combined:
                # Avoid false matches - check it's not "light" in "lightweight" or "flight"
                if "light" in combined and not any(skip in combined for skip in ["lightweight", "flight", "highlight", "lightning"]):
                    return {
                        "device_id": device_id,
                        "device_type": "light",
                        "device_category": "lighting"
                    }
            
            # Media players (check before "tv" to avoid false matches like "ATV")
            if any(keyword in combined for keyword in ["television", "frame tv", "samsung tv", "sony tv", "lg tv"]):
                # Avoid matching "ATV" (all-terrain vehicle) - check it's not standalone "atv"
                if " atv " in combined or combined.endswith(" atv") or combined.startswith("atv "):
                    pass  # Skip - might be all-terrain vehicle
                else:
                    return {
                        "device_id": device_id,
                        "device_type": "media_player",
                        "device_category": "entertainment"
                    }
            elif "tv" in combined and "atv" not in combined.lower():  # Avoid "ATV"
                return {
                    "device_id": device_id,
                    "device_type": "media_player",
                    "device_category": "entertainment"
                }
            
            # Switches and outlets
            elif any(keyword in combined for keyword in ["switch", "outlet", "smart plug", "smartplug"]):
                return {
                    "device_id": device_id,
                    "device_type": "switch",
                    "device_category": "control"
                }
            elif "plug" in combined and "smart" in combined:
                return {
                    "device_id": device_id,
                    "device_type": "switch",
                    "device_category": "control"
                }
            
            # Sensors
            elif any(keyword in combined for keyword in ["sensor", "motion", "presence", "temperature", "humidity", "binary_sensor"]):
                return {
                    "device_id": device_id,
                    "device_type": "sensor",
                    "device_category": "sensor"
                }
            
            # Vacuum
            elif any(keyword in combined for keyword in ["vacuum", "roborock", "robotic vacuum", "dock"]):
                return {
                    "device_id": device_id,
                    "device_type": "vacuum",
                    "device_category": "appliance"
                }
            
            # Thermostat
            elif any(keyword in combined for keyword in ["thermostat", "climate", "hvac"]):
                return {
                    "device_id": device_id,
                    "device_type": "thermostat",
                    "device_category": "climate"
                }
            
            # Lock
            elif any(keyword in combined for keyword in ["lock", "door lock", "smart lock"]):
                return {
                    "device_id": device_id,
                    "device_type": "lock",
                    "device_category": "security"
                }
            
            # Camera
            elif any(keyword in combined for keyword in ["camera", "cam", "security camera", "stick up cam"]):
                return {
                    "device_id": device_id,
                    "device_type": "camera",
                    "device_category": "security"
                }
            
            # Fan
            elif any(keyword in combined for keyword in ["fan", "ceiling fan"]):
                return {
                    "device_id": device_id,
                    "device_type": "fan",
                    "device_category": "climate"
                }
            
            # Button/Remote
            elif any(keyword in combined for keyword in ["button", "smart button", "remote"]):
                return {
                    "device_id": device_id,
                    "device_type": "button",
                    "device_category": "control"
                }
            
            # TV/Media Player (fallback - check after other patterns)
            elif "tv" in combined:
                return {
                    "device_id": device_id,
                    "device_type": "media_player",
                    "device_category": "entertainment"
                }
            
            return {
                "device_id": device_id,
                "device_type": None,
                "device_category": None
            }
            
        except Exception as e:
            logger.error(f"Error classifying device {device_id} by metadata: {e}")
            return {
                "device_id": device_id,
                "device_type": None,
                "device_category": None
            }


# Singleton instance
_classifier_service: DeviceClassifierService | None = None


def get_classifier_service() -> DeviceClassifierService:
    """Get singleton classifier service instance"""
    global _classifier_service
    if _classifier_service is None:
        _classifier_service = DeviceClassifierService()
    return _classifier_service

