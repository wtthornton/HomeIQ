"""
Capability Normalization Utilities

Provides unified capability handling across different data sources:
- Device intelligence service (uses 'name', 'type', 'properties')
- Data API service (uses 'feature', 'supported')
- Legacy database (uses 'capability_name', 'feature')
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def normalize_capability(cap: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize capability from any source to unified format.
    
    Handles:
    - Device intelligence (uses 'name', 'type', 'properties')
    - Data API (uses 'feature', 'supported')
    - Legacy (uses 'capability_name', 'feature')
    
    Args:
        cap: Capability dictionary from any source
        
    Returns:
        Normalized capability with: name, type, properties, supported, source
        
    Example:
        >>> cap = {"name": "brightness", "type": "numeric", "properties": {"min": 0, "max": 100}}
        >>> normalize_capability(cap)
        {"name": "brightness", "type": "numeric", "properties": {"min": 0, "max": 100}, "supported": True, "source": "unknown"}
    """
    if not isinstance(cap, dict):
        logger.warning(f"Capability not a dict: {type(cap)}")
        return _empty_capability()

    # Try different field names for name/feature
    name = cap.get('name') or cap.get('feature') or cap.get('capability_name', 'unknown')

    # Try different field names for type
    cap_type = cap.get('type') or cap.get('capability_type', 'unknown')

    # Properties might be in different locations
    properties = cap.get('properties') or cap.get('attributes') or {}

    # Support status - check multiple possible fields
    supported = cap.get('supported', cap.get('exposed', cap.get('configured', True)))

    # Determine source
    source = cap.get('source', 'unknown')

    return {
        'name': name,
        'type': cap_type,
        'properties': properties,
        'supported': bool(supported),
        'source': source
    }


def format_capability_for_display(cap: dict[str, Any]) -> str:
    """
    Format capability for display in prompts with full details.
    
    Args:
        cap: Capability dictionary (should be normalized)
        
    Returns:
        Formatted string like "✓ brightness (numeric, 0-100%)"
        
    Example:
        >>> cap = {"name": "brightness", "type": "numeric", "properties": {"min": 0, "max": 100, "unit": "%"}, "supported": True}
        >>> format_capability_for_display(cap)
        "✓ brightness (numeric) [0-100 %]"
    """
    # Normalize if not already
    normalized = normalize_capability(cap) if isinstance(cap, dict) else _empty_capability()

    name = normalized.get('name', 'unknown')
    cap_type = normalized.get('type', 'unknown')
    properties = normalized.get('properties', {})
    supported = normalized.get('supported', True)

    # Build description
    desc = name
    if cap_type != 'unknown':
        desc += f" ({cap_type})"

    # Add details based on type
    if cap_type == 'numeric' and properties:
        min_val = properties.get('min') or properties.get('value_min')
        max_val = properties.get('max') or properties.get('value_max')
        unit = properties.get('unit', '')

        if min_val is not None and max_val is not None:
            unit_str = f" {unit}" if unit else ""
            desc += f" [{min_val}-{max_val}{unit_str}]"

    elif cap_type == 'enum' and properties:
        values = properties.get('values') or properties.get('enum', [])
        if isinstance(values, list) and len(values) <= 8:
            values_str = ', '.join(map(str, values))
            if len(values_str) <= 40:
                desc += f" [{values_str}]"
            else:
                desc += f" [{values_str[:37]}...]"

    elif cap_type == 'composite' and 'features' in properties:
        features = properties['features']
        if isinstance(features, list) and len(features) <= 3:
            feature_names = [f.get('name', 'unknown') for f in features if isinstance(f, dict)]
            desc += f" [{', '.join(feature_names)}]"

    elif cap_type == 'binary' and 'values' in properties:
        values = properties['values']
        if isinstance(values, list) and len(values) == 2:
            desc += f" {values}"

    # Add support status
    status = "✓" if supported else "✗"
    return f"{status} {desc}"


def _empty_capability() -> dict[str, Any]:
    """Return empty capability structure."""
    return {
        'name': 'unknown',
        'type': 'unknown',
        'properties': {},
        'supported': False,
        'source': 'unknown'
    }


def extract_capability_values(cap: dict[str, Any], value_type: str) -> list[Any] | None:
    """
    Extract capability values (enum values, numeric range, etc.) for YAML generation.
    
    Args:
        cap: Normalized capability dictionary
        value_type: Type of value to extract ('enum', 'range', etc.)
        
    Returns:
        List of values or None
        
    Example:
        >>> cap = {"name": "speed", "type": "enum", "properties": {"values": ["off", "low", "high"]}}
        >>> extract_capability_values(cap, "enum")
        ["off", "low", "high"]
    """
    normalized = normalize_capability(cap) if isinstance(cap, dict) else _empty_capability()
    properties = normalized.get('properties', {})

    if value_type == 'enum' and normalized.get('type') == 'enum':
        return properties.get('values') or properties.get('enum', [])

    elif value_type == 'range' and normalized.get('type') == 'numeric':
        min_val = properties.get('min') or properties.get('value_min')
        max_val = properties.get('max') or properties.get('value_max')
        if min_val is not None and max_val is not None:
            return [min_val, max_val]

    return None


def has_capability(entities: list[dict[str, Any]], capability_name: str) -> bool:
    """
    Check if any entity has a specific capability.
    
    Args:
        entities: List of entity dictionaries
        capability_name: Name of capability to check for
        
    Returns:
        True if any entity has the capability
    """
    for entity in entities:
        capabilities = entity.get('capabilities', [])
        for cap in capabilities:
            normalized = normalize_capability(cap)
            if normalized.get('name', '').lower() == capability_name.lower():
                return normalized.get('supported', False)
    return False

