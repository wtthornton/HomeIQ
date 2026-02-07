"""
Device Pattern Definitions
Phase 2.1: Patterns for identifying device types from entities
"""

from typing import Any


# Device patterns: required and optional entity types/attributes
DEVICE_PATTERNS: dict[str, dict[str, Any]] = {
    "fridge": {
        "required": ["temperature", "door"],
        "optional": ["light", "humidity", "water_leak"],
        "description": "Refrigerator with temperature sensors and door sensor"
    },
    "car": {
        "required": ["location", "battery"],
        "optional": ["charging", "range", "lock"],
        "description": "Vehicle with location tracking and battery"
    },
    "3d_printer": {
        "required": ["temperature", "progress"],
        "optional": ["status", "bed_temperature"],
        "description": "3D printer with temperature and progress tracking"
    },
    "thermostat": {
        "required": ["temperature", "mode"],
        "optional": ["humidity", "fan", "setpoint"],
        "description": "Thermostat with temperature and mode control"
    },
    "light": {
        "required": ["brightness", "state"],
        "optional": ["color", "color_temp", "effect"],
        "description": "Light with brightness control"
    },
    "sensor": {
        "required": ["state"],
        "optional": ["battery", "temperature", "humidity"],
        "description": "Generic sensor device"
    },
    "switch": {
        "required": ["state"],
        "optional": ["power", "current", "voltage"],
        "description": "Switch or outlet"
    },
    "camera": {
        "required": ["stream"],
        "optional": ["motion", "recording"],
        "description": "Camera device"
    },
    "lock": {
        "required": ["lock_state"],
        "optional": ["battery", "keypad"],
        "description": "Smart lock"
    },
    "fan": {
        "required": ["state", "speed"],
        "optional": ["oscillate", "direction"],
        "description": "Fan with speed control"
    }
}


# Domain-to-device-type mapping (primary classification method)
DOMAIN_TO_DEVICE_TYPE: dict[str, str] = {
    # Lighting
    "light": "light",

    # Switches and outlets
    "switch": "switch",

    # Sensors
    "sensor": "sensor",
    "binary_sensor": "sensor",

    # Climate
    "climate": "thermostat",
    "fan": "fan",

    # Security
    "lock": "lock",
    "camera": "camera",
    "alarm_control_panel": "alarm",

    # Covers
    "cover": "cover",
    "garage_door": "cover",

    # Media
    "media_player": "media_player",

    # Vacuum
    "vacuum": "vacuum",

    # Other
    "valve": "valve",
    "button": "button",
    "remote": "remote",
}

# Priority order for domain-based classification (most specific first)
DOMAIN_PRIORITY = [
    "light", "switch", "climate", "fan", "lock", "camera",
    "alarm_control_panel", "sensor", "binary_sensor", "cover",
    "media_player", "vacuum", "garage_door", "valve", "button", "remote"
]


def match_device_pattern(
    entity_domains: list[str],
    attribute_keys: set[str]
) -> tuple[str | None, float]:
    """
    Match entities to device patterns.

    Uses domain-based classification as primary method, with pattern matching as fallback.

    Args:
        entity_domains: List of entity domains (sensor, light, etc.)
        attribute_keys: Set of attribute key names across all entities

    Returns:
        Tuple of (matched device type or None, confidence score 0.0-1.0)
    """
    if not entity_domains:
        return None, 0.0

    # PRIMARY: Domain-based classification (most reliable)
    # Check domains in priority order
    for domain in DOMAIN_PRIORITY:
        if domain in entity_domains:
            device_type = DOMAIN_TO_DEVICE_TYPE.get(domain)
            if device_type:
                # Domain match is high confidence; more matching domains = higher
                domain_count = sum(1 for d in entity_domains if d == domain)
                total = len(entity_domains)
                # Base confidence 0.7, boosted by domain prevalence (up to 0.95)
                confidence = min(0.7 + 0.25 * (domain_count / max(total, 1)), 0.95)
                return device_type, round(confidence, 3)

    # FALLBACK: Try any domain in mapping
    for domain in entity_domains:
        device_type = DOMAIN_TO_DEVICE_TYPE.get(domain)
        if device_type:
            return device_type, 0.6

    # SECONDARY: Pattern-based matching (for complex devices)
    # Build feature set from entities
    features = set()
    for domain in entity_domains:
        features.add(domain)

    # Add attribute keys as features
    features.update(attribute_keys)

    # Score each pattern
    best_match = None
    best_score = 0.0
    best_raw_score = 0.0
    best_max_score = 1.0

    for device_type, pattern in DEVICE_PATTERNS.items():
        required = set(pattern["required"])
        optional = set(pattern.get("optional", []))

        # Check required features
        required_matches = len(required.intersection(features))
        if required_matches < len(required):
            continue  # Missing required features

        # Calculate score: required features worth 2 points, optional worth 1
        optional_matches = len(optional.intersection(features))
        raw_score = required_matches * 2 + optional_matches
        max_possible = len(required) * 2 + len(optional)

        if raw_score > best_raw_score:
            best_raw_score = raw_score
            best_max_score = max_possible
            best_match = device_type

    if best_match and best_max_score > 0:
        # Normalize to 0.3-0.85 range for pattern matches (lower than domain matches)
        normalized = best_raw_score / best_max_score
        confidence = round(0.3 + 0.55 * normalized, 3)
        return best_match, confidence

    return None, 0.0


def get_device_category(device_type: str | None) -> str | None:
    """
    Get device category from device type.

    Args:
        device_type: Device type (fridge, light, etc.)

    Returns:
        Device category (appliance, lighting, etc.)
    """
    category_map = {
        "fridge": "appliance",
        "car": "vehicle",
        "3d_printer": "appliance",
        "thermostat": "climate",
        "light": "lighting",
        "sensor": "sensor",
        "switch": "control",
        "camera": "security",
        "lock": "security",
        "fan": "climate",
        "alarm": "security",
        "cover": "cover",
        "media_player": "entertainment",
        "vacuum": "appliance",
        "valve": "plumbing",
        "button": "control",
        "remote": "control",
    }
    return category_map.get(device_type) if device_type else None
