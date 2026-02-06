"""
Device Name Generator

Pattern-based name generation for devices (fast, no AI required).
"""

import logging
import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from ...models.database import Device, DeviceEntity

logger = logging.getLogger(__name__)

# Import AI suggester (optional)
try:
    from .ai_suggester import AINameSuggester
except ImportError:
    AINameSuggester = None


@dataclass
class NameSuggestion:
    """Name suggestion result"""
    name: str
    confidence: float  # 0.0-1.0
    source: str  # "pattern", "ai", "local_llm", "preference"
    reasoning: str | None = None


class DeviceNameGenerator:
    """Generate human-readable device names with resource efficiency"""

    def __init__(self, settings: Any = None):
        self.settings = settings
        # Use bounded LRU-style cache to prevent unbounded growth (LOW-5)
        self._pattern_cache_max_size = 1000
        self.pattern_cache: OrderedDict[str, NameSuggestion] = OrderedDict()
        self.ai_suggester = None
        
        # Initialize AI suggester if available
        if AINameSuggester and settings:
            try:
                self.ai_suggester = AINameSuggester(settings)
            except Exception as e:
                logger.warning(f"Failed to initialize AI suggester: {e}")

        # Common device type mappings
        self.device_type_map = {
            "light": "Light",
            "switch": "Switch",
            "sensor": "Sensor",
            "binary_sensor": "Sensor",
            "climate": "Thermostat",
            "cover": "Cover",
            "lock": "Lock",
            "fan": "Fan",
            "camera": "Camera",
            "media_player": "Media Player",
        }

        # Position patterns from entity IDs
        self.position_patterns = {
            r"_1_1|_1$": "Front Left",
            r"_1_2|_2$": "Front Right",
            r"_1_3|_3$": "Back Left",
            r"_1_4|_4$": "Back Right",
            r"_1_5|_5$": "Center Left",
            r"_1_6|_6$": "Center Right",
            r"_2_1": "Front Left",
            r"_2_2": "Front Right",
            r"_2_3": "Back Left",
            r"_2_4": "Back Right",
        }

    async def generate_suggested_name(
        self,
        device: Device,
        entity: DeviceEntity | None = None,
        context: dict[str, Any] | None = None,
        use_ai: bool = False
    ) -> NameSuggestion:
        """
        Generate name suggestion using tiered approach:
        
        1. Pattern-based (fast, no AI) - 90% of cases
        2. AI generation (optional) - complex cases only
        3. Local LLM (optional) - privacy-sensitive users
        
        Returns suggestion with confidence score and source.
        """
        # Try pattern-based first (fast, no AI)
        suggestion = self._pattern_based_generation(device, entity)
        
        # If pattern-based has low confidence and AI is requested, try AI
        if use_ai and self.ai_suggester and suggestion.confidence < 0.5:
            try:
                ai_suggestions = await self.ai_suggester.suggest_name(device, entity, context)
                if ai_suggestions:
                    # Return highest confidence AI suggestion
                    return max(ai_suggestions, key=lambda s: s.confidence)
            except Exception as e:
                logger.warning(f"AI suggestion failed, using pattern-based: {e}")
        
        return suggestion

    def _cache_put(self, key: str, value: NameSuggestion) -> None:
        """Insert into bounded OrderedDict cache, evicting oldest if full."""
        if key in self.pattern_cache:
            # Move to end (most recently used)
            self.pattern_cache.move_to_end(key)
            self.pattern_cache[key] = value
        else:
            if len(self.pattern_cache) >= self._pattern_cache_max_size:
                # Evict the oldest (first) entry
                self.pattern_cache.popitem(last=False)
            self.pattern_cache[key] = value

    def _pattern_based_generation(
        self,
        device: Device,
        entity: DeviceEntity | None = None
    ) -> NameSuggestion:
        """
        Fast pattern-based name generation (no AI).

        Strategies:
        - Location + Device Type: "Office Light"
        - Extract position from entity_id: "hue_1_6" → "Back Left"
        - Manufacturer + Location: "Philips Office Light"

        Performance: <10ms per device
        """
        # Check cache first
        cache_key = f"{device.id}_{entity.entity_id if entity else 'none'}"
        if cache_key in self.pattern_cache:
            return self.pattern_cache[cache_key]

        # Strategy 1: Location + Device Type (highest confidence)
        if device.area_name:
            device_type = self._extract_device_type(device, entity)
            if device_type:
                name = f"{device.area_name} {device_type}"
                reasoning = f"Based on location ({device.area_name}) and device type ({device_type})"
                suggestion = NameSuggestion(
                    name=name,
                    confidence=0.9,
                    source="pattern",
                    reasoning=reasoning
                )
                self._cache_put(cache_key, suggestion)
                return suggestion

        # Strategy 2: Extract position from entity_id
        if entity and entity.entity_id:
            position = self._extract_position_from_entity_id(entity.entity_id)
            if position:
                device_type = self._extract_device_type(device, entity) or "Device"
                if device.area_name:
                    name = f"{device.area_name} {position} {device_type}"
                else:
                    name = f"{position} {device_type}"
                reasoning = f"Extracted position '{position}' from entity ID pattern"
                suggestion = NameSuggestion(
                    name=name,
                    confidence=0.85,
                    source="pattern",
                    reasoning=reasoning
                )
                self._cache_put(cache_key, suggestion)
                return suggestion

        # Strategy 3: Manufacturer + Location
        if device.manufacturer and device.manufacturer != "Unknown":
            device_type = self._extract_device_type(device, entity) or "Device"
            if device.area_name:
                name = f"{device.area_name} {device.manufacturer} {device_type}"
            else:
                name = f"{device.manufacturer} {device_type}"
            reasoning = f"Based on manufacturer ({device.manufacturer}) and device type"
            suggestion = NameSuggestion(
                name=name,
                confidence=0.7,
                source="pattern",
                reasoning=reasoning
            )
            self._cache_put(cache_key, suggestion)
            return suggestion

        # Strategy 4: Clean up existing name
        if device.name:
            cleaned_name = self._clean_device_name(device.name)
            if cleaned_name != device.name:
                suggestion = NameSuggestion(
                    name=cleaned_name,
                    confidence=0.6,
                    source="pattern",
                    reasoning="Cleaned up existing device name"
                )
                self._cache_put(cache_key, suggestion)
                return suggestion

        # Fallback: Use existing name or generic
        fallback_name = device.name or "Device"
        suggestion = NameSuggestion(
            name=fallback_name,
            confidence=0.3,
            source="pattern",
            reasoning="Fallback to existing name"
        )
        self._cache_put(cache_key, suggestion)
        return suggestion

    def _extract_device_type(self, device: Device, entity: DeviceEntity | None = None) -> str | None:
        """Extract device type from entity domain or device class"""
        if entity:
            domain = entity.domain
            if domain in self.device_type_map:
                return self.device_type_map[domain]
        
        if device.device_class:
            # Capitalize device class
            return device.device_class.replace("_", " ").title()
        
        return None

    def _extract_position_from_entity_id(self, entity_id: str) -> str | None:
        """Extract position information from entity ID patterns"""
        # Look for position patterns in entity ID
        for pattern, position in self.position_patterns.items():
            if re.search(pattern, entity_id):
                return position
        
        # Try to extract numbers that might indicate position
        # e.g., "hue_color_downlight_1_6" -> "1_6" -> "Back Left"
        match = re.search(r"_(\d+)_(\d+)$", entity_id)
        if match:
            first, second = match.groups()
            # Simple mapping: 1_6 -> Back Left, 2_2 -> Front Right, etc.
            if first == "1" and second == "6":
                return "Back Left"
            elif first == "1" and second == "7":
                return "Back Right"
            elif first == "2" and second == "2":
                return "Front Right"
            # Add more mappings as needed
        
        return None

    def _clean_device_name(self, name: str) -> str:
        """Clean up device name by removing technical terms"""
        # Remove common technical prefixes/suffixes
        cleaned = name
        
        # Remove model numbers (e.g., "E27 WS opal 980lm")
        cleaned = re.sub(r'\bE\d+\b', '', cleaned)
        cleaned = re.sub(r'\b\d+lm\b', '', cleaned)
        cleaned = re.sub(r'\bWS\b', '', cleaned)
        
        # Remove version numbers
        cleaned = re.sub(r'\bv?\d+\.\d+\.\d+\b', '', cleaned)
        
        # Remove manufacturer if it's redundant
        cleaned = re.sub(r'\b(Philips|Hue|IKEA|TRADFRI|Xiaomi)\s+', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned

