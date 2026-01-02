"""
Context Filtering Service

Phase 3.2: Dynamic Context Filtering (Score: 58)

Extracts intent from user prompt (area, device type, service) and
filters devices/entities/services to include only relevant context.
This reduces token usage while maintaining accuracy.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class ContextFilteringService:
    """
    Service for filtering context based on user intent extraction.
    
    Extracts intent (area, device type, service) from user prompt and
    filters context to include only relevant items.
    """

    def __init__(self):
        """Initialize context filtering service."""
        self.logger = logger

    def extract_intent(self, user_prompt: str) -> dict[str, Any]:
        """
        Extract intent from user prompt.
        
        Args:
            user_prompt: User's natural language prompt
            
        Returns:
            Dictionary with extracted intent:
            {
                "areas": ["office", "bedroom"],
                "device_types": ["light", "sensor"],
                "services": ["light.turn_on"],
                "domains": ["light", "sensor"]
            }
        """
        prompt_lower = user_prompt.lower()
        intent = {
            "areas": [],
            "device_types": [],
            "services": [],
            "domains": []
        }
        
        # Common area names (can be extended)
        area_keywords = [
            "office", "bedroom", "living room", "kitchen", "bathroom",
            "garage", "basement", "attic", "hallway", "dining room",
            "outdoor", "garden", "patio", "backyard", "front yard"
        ]
        
        # Extract areas
        for area in area_keywords:
            if area in prompt_lower:
                intent["areas"].append(area.replace(" ", "_"))
        
        # Extract device types/domains
        domain_keywords = {
            "light": ["light", "lamp", "bulb", "brightness", "illuminate", "illumination"],
            "sensor": ["sensor", "detect", "motion", "temperature", "humidity", "presence"],
            "switch": ["switch", "turn on", "turn off", "toggle"],
            "climate": ["climate", "temperature", "heat", "cool", "hvac", "thermostat", "heating", "cooling"],
            "cover": ["cover", "blind", "shade", "curtain", "garage door"],
            "fan": ["fan", "ventilate", "air"],
            "lock": ["lock", "unlock", "door lock"],
            "media_player": ["media", "music", "speaker", "play", "volume", "audio"],
            "camera": ["camera", "video", "record"],
            "alarm": ["alarm", "alert", "notification"],
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                intent["domains"].append(domain)
                intent["device_types"].append(domain)
        
        # Extract services (common patterns)
        service_patterns = [
            (r"turn\s+on", "turn_on"),
            (r"turn\s+off", "turn_off"),
            (r"toggle", "toggle"),
            (r"set\s+(?:brightness|temperature|volume)", "set"),
            (r"dim", "set_brightness"),
            (r"brighten", "set_brightness"),
        ]
        
        for pattern, service_action in service_patterns:
            if re.search(pattern, prompt_lower):
                # Try to infer domain from context
                for domain in intent["domains"]:
                    service = f"{domain}.{service_action}"
                    if service not in intent["services"]:
                        intent["services"].append(service)
        
        return intent

    def filter_entities(
        self,
        entities: list[dict[str, Any]],
        intent: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Filter entities based on extracted intent.
        
        Args:
            entities: List of entity dictionaries
            intent: Extracted intent dictionary
            
        Returns:
            Filtered list of entities matching intent
        """
        if not intent.get("domains") and not intent.get("areas"):
            # No filtering criteria - return all
            return entities
        
        filtered = []
        
        for entity in entities:
            entity_domain = (entity.get("domain") or "").lower()
            entity_area_id = (entity.get("area_id") or "").lower()
            
            # Check domain match
            domain_match = False
            if intent.get("domains"):
                domain_match = entity_domain in intent["domains"]
            else:
                # No domain filter - match all
                domain_match = True
            
            # Check area match
            area_match = False
            if intent.get("areas"):
                # Check if entity area matches any intent area
                for intent_area in intent["areas"]:
                    if intent_area in entity_area_id or entity_area_id in intent_area:
                        area_match = True
                        break
            else:
                # No area filter - match all
                area_match = True
            
            # Include if matches domain AND area (if both specified)
            if domain_match and area_match:
                filtered.append(entity)
        
        return filtered

    def filter_devices(
        self,
        devices: list[dict[str, Any]],
        intent: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Filter devices based on extracted intent.
        
        Args:
            devices: List of device dictionaries
            intent: Extracted intent dictionary
            
        Returns:
            Filtered list of devices matching intent
        """
        if not intent.get("device_types") and not intent.get("areas"):
            # No filtering criteria - return all
            return devices
        
        filtered = []
        
        for device in devices:
            device_area_id = (device.get("area_id") or "").lower()
            device_name = (device.get("name") or device.get("device_id") or "").lower()
            
            # Check device type match (by name/manufacturer/model)
            type_match = False
            if intent.get("device_types"):
                # Check if device name contains any device type keyword
                for device_type in intent["device_types"]:
                    if device_type in device_name:
                        type_match = True
                        break
            else:
                # No type filter - match all
                type_match = True
            
            # Check area match
            area_match = False
            if intent.get("areas"):
                for intent_area in intent["areas"]:
                    if intent_area in device_area_id or device_area_id in intent_area:
                        area_match = True
                        break
            else:
                # No area filter - match all
                area_match = True
            
            # Include if matches type AND area (if both specified)
            if type_match and area_match:
                filtered.append(device)
        
        return filtered

    def filter_services(
        self,
        services: list[str],
        intent: dict[str, Any]
    ) -> list[str]:
        """
        Filter services based on extracted intent.
        
        Args:
            services: List of service names
            intent: Extracted intent dictionary
            
        Returns:
            Filtered list of services matching intent
        """
        if not intent.get("services") and not intent.get("domains"):
            # No filtering criteria - return all
            return services
        
        filtered = []
        
        for service in services:
            service_lower = service.lower()
            
            # Check exact service match
            if intent.get("services"):
                if any(intent_service.lower() in service_lower for intent_service in intent["services"]):
                    filtered.append(service)
                    continue
            
            # Check domain match
            if intent.get("domains"):
                for domain in intent["domains"]:
                    if service_lower.startswith(f"{domain}."):
                        filtered.append(service)
                        break
        
        return filtered
