"""
Trigger Condition Analyzer

Analyzes natural language queries to identify trigger conditions for automations.
Extracts trigger types (presence, motion, door, window, temperature) and location context.

Part of Phase 1: Trigger Device Discovery for Presence Sensor Detection
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class TriggerConditionAnalyzer:
    """
    Analyzes queries to identify trigger conditions that require sensors.

    Example:
        query = "When I sit at my desk, turn on the lights"
        conditions = await analyzer.analyze_trigger_conditions(query, entities)
        # Returns: [{
        #     'trigger_type': 'presence',
        #     'required_device_class': 'occupancy',
        #     'required_sensor_type': 'binary_sensor',
        #     'location': 'desk',
        #     'confidence': 0.85
        # }]
    """

    # Trigger type patterns
    PRESENCE_PATTERNS = [
        r"\b(presence|occupancy|detected|someone|anyone|person)\b",
        r"\b(sit|sit down|sitting|arrive|arrives|arrival)\b",
        r"\b(present|arrive|enter)\b",
    ]

    MOTION_PATTERNS = [
        r"\b(motion|movement|moving|moves|moved)\b",
        r"\b(walk|walks|walking|enter|enters|entering)\b",
    ]

    DOOR_PATTERNS = [
        r"\b(door|doors)\b.*\b(open|opens|opened|close|closes|closed)\b",
        r"\b(open|opens|opened|close|closes|closed).* door",
    ]

    WINDOW_PATTERNS = [
        r"\b(window|windows)\b.*\b(open|opens|opened|close|closes|closed)\b",
        r"\b(open|opens|opened|close|closes|closed).* window",
    ]

    TEMPERATURE_PATTERNS = [
        r"\b(temperature|temp|hot|cold|cooler|warmer)\b",
        r"\b(above|below|over|under).*\b(degrees?|°)\b",
    ]

    # Location extraction patterns
    LOCATION_PATTERNS = [
        r"\b(at|in|near|inside|outside)\s+([a-zA-Z\s]+?)(?:\s|,|$)",
        r"\b(desk|office|bedroom|kitchen|living room|bathroom|garage|hallway|entrance)\b",
    ]

    def __init__(self):
        """Initialize the trigger condition analyzer."""
        # Compile regex patterns for better performance
        self.presence_re = [re.compile(pattern, re.IGNORECASE) for pattern in self.PRESENCE_PATTERNS]
        self.motion_re = [re.compile(pattern, re.IGNORECASE) for pattern in self.MOTION_PATTERNS]
        self.door_re = [re.compile(pattern, re.IGNORECASE) for pattern in self.DOOR_PATTERNS]
        self.window_re = [re.compile(pattern, re.IGNORECASE) for pattern in self.WINDOW_PATTERNS]
        self.temp_re = [re.compile(pattern, re.IGNORECASE) for pattern in self.TEMPERATURE_PATTERNS]
        self.location_re = [re.compile(pattern, re.IGNORECASE) for pattern in self.LOCATION_PATTERNS]

    async def analyze_trigger_conditions(
        self,
        query: str,
        extracted_entities: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze query to identify trigger conditions.

        Args:
            query: Natural language query string
            extracted_entities: Already extracted entities (optional, for location context)

        Returns:
            List of trigger condition dictionaries with:
            - trigger_type: 'presence', 'motion', 'door', 'window', 'temperature'
            - required_device_class: Home Assistant device class
            - required_sensor_type: 'binary_sensor' or 'sensor'
            - location: Location context if found
            - confidence: Confidence score (0.0-1.0)
        """
        if not query or not query.strip():
            return []

        query_lower = query.lower()
        conditions = []

        # Extract location context from entities or query
        location = self._extract_location(query, extracted_entities)

        # Check for presence triggers
        presence_condition = self._check_presence_trigger(query, query_lower, location)
        if presence_condition:
            conditions.append(presence_condition)

        # Check for motion triggers
        motion_condition = self._check_motion_trigger(query, query_lower, location)
        if motion_condition:
            conditions.append(motion_condition)

        # Check for door triggers
        door_condition = self._check_door_trigger(query, query_lower, location)
        if door_condition:
            conditions.append(door_condition)

        # Check for window triggers
        window_condition = self._check_window_trigger(query, query_lower, location)
        if window_condition:
            conditions.append(window_condition)

        # Check for temperature triggers
        temp_condition = self._check_temperature_trigger(query, query_lower, location)
        if temp_condition:
            conditions.append(temp_condition)

        logger.debug(f"Analyzed query '{query}': found {len(conditions)} trigger conditions")
        return conditions

    def _check_presence_trigger(
        self,
        query: str,
        query_lower: str,
        location: str | None,
    ) -> dict[str, Any] | None:
        """Check if query contains presence trigger condition."""
        for pattern in self.presence_re:
            if pattern.search(query_lower):
                return {
                    "trigger_type": "presence",
                    "required_device_class": "occupancy",
                    "required_sensor_type": "binary_sensor",
                    "location": location,
                    "confidence": 0.85,
                    "matched_text": pattern.search(query_lower).group(0),
                }
        return None

    def _check_motion_trigger(
        self,
        query: str,
        query_lower: str,
        location: str | None,
    ) -> dict[str, Any] | None:
        """Check if query contains motion trigger condition."""
        for pattern in self.motion_re:
            if pattern.search(query_lower):
                return {
                    "trigger_type": "motion",
                    "required_device_class": "motion",
                    "required_sensor_type": "binary_sensor",
                    "location": location,
                    "confidence": 0.80,
                    "matched_text": pattern.search(query_lower).group(0),
                }
        return None

    def _check_door_trigger(
        self,
        query: str,
        query_lower: str,
        location: str | None,
    ) -> dict[str, Any] | None:
        """Check if query contains door trigger condition."""
        for pattern in self.door_re:
            if pattern.search(query_lower):
                return {
                    "trigger_type": "door",
                    "required_device_class": "door",
                    "required_sensor_type": "binary_sensor",
                    "location": location,
                    "confidence": 0.90,
                    "matched_text": pattern.search(query_lower).group(0),
                }
        return None

    def _check_window_trigger(
        self,
        query: str,
        query_lower: str,
        location: str | None,
    ) -> dict[str, Any] | None:
        """Check if query contains window trigger condition."""
        for pattern in self.window_re:
            if pattern.search(query_lower):
                return {
                    "trigger_type": "window",
                    "required_device_class": "window",
                    "required_sensor_type": "binary_sensor",
                    "location": location,
                    "confidence": 0.90,
                    "matched_text": pattern.search(query_lower).group(0),
                }
        return None

    def _check_temperature_trigger(
        self,
        query: str,
        query_lower: str,
        location: str | None,
    ) -> dict[str, Any] | None:
        """Check if query contains temperature trigger condition."""
        for pattern in self.temp_re:
            if pattern.search(query_lower):
                return {
                    "trigger_type": "temperature",
                    "required_device_class": "temperature",
                    "required_sensor_type": "sensor",
                    "location": location,
                    "confidence": 0.85,
                    "matched_text": pattern.search(query_lower).group(0),
                }
        return None

    def _extract_location(
        self,
        query: str,
        extracted_entities: list[dict[str, Any]] | None = None,
    ) -> str | None:
        """
        Extract location context from query or entities.

        Args:
            query: Natural language query
            extracted_entities: Already extracted entities

        Returns:
            Location string or None
        """
        # First, try to get location from extracted entities (area entities)
        if extracted_entities:
            for entity in extracted_entities:
                if entity.get("type") == "area":
                    area_name = entity.get("name") or entity.get("area_name")
                    if area_name:
                        return area_name.lower()

        # Then, try to extract from query using patterns
        query_lower = query.lower()

        # Common location keywords
        locations = [
            "desk", "office", "bedroom", "kitchen", "living room",
            "bathroom", "garage", "hallway", "entrance", "dining room",
            "study", "workshop", "basement", "attic",
        ]

        for location in locations:
            if location in query_lower:
                return location

        # Try pattern-based extraction
        for pattern in self.location_re:
            match = pattern.search(query)
            if match:
                # Extract the location part (second group)
                if len(match.groups()) >= 2:
                    location_text = match.group(2).strip()
                    # Clean up common prepositions
                    location_text = re.sub(r"^(at|in|near|inside|outside)\s+", "", location_text, flags=re.IGNORECASE)
                    if location_text:
                        return location_text.lower()

        return None


