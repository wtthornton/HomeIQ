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


def match_device_pattern(entity_domains: list[str], entity_attributes: dict[str, Any]) -> str | None:
    """
    Match entities to device patterns.
    
    Args:
        entity_domains: List of entity domains (sensor, light, etc.)
        entity_attributes: Dictionary of entity attributes
        
    Returns:
        Matched device type or None
    """
    # Build feature set from entities
    features = set()
    for domain in entity_domains:
        features.add(domain)
    
    # Add attributes as features
    for attr_key, attr_value in entity_attributes.items():
        if isinstance(attr_value, (str, int, float, bool)):
            features.add(attr_key)
    
    # Score each pattern
    best_match = None
    best_score = 0.0
    
    for device_type, pattern in DEVICE_PATTERNS.items():
        required = set(pattern["required"])
        optional = set(pattern.get("optional", []))
        
        # Check required features
        required_matches = len(required.intersection(features))
        if required_matches < len(required):
            continue  # Missing required features
        
        # Calculate score
        optional_matches = len(optional.intersection(features))
        score = required_matches * 2 + optional_matches
        
        if score > best_score:
            best_score = score
            best_match = device_type
    
    return best_match


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
        "fan": "climate"
    }
    return category_map.get(device_type) if device_type else None

