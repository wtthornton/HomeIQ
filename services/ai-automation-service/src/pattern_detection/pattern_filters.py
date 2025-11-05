"""
Pattern Filtering Constants and Utilities

Filters out low-quality patterns that aren't useful for automation.
"""

# Domains that are NOT actionable for automation
EXCLUDED_DOMAINS = [
    'sensor',      # Most sensors don't represent user actions
    'event',       # System events
    'image',       # Camera images
    'counter',     # Counters
    'input_number', # Configuration
]

# Domains that ARE actionable for automation
ACTIONABLE_DOMAINS = [
    'light',
    'switch',
    'cover',
    'climate',
    'fan',
    'lock',
    'scene',
    'automation',
    'script',
    'media_player',
]

# Entity prefixes to exclude (system sensors, etc.)
EXCLUDED_PREFIXES = [
    'sensor.home_assistant_',  # System sensors
    'sensor.slzb_',            # Zigbee coordinator
    'sensor.*_battery_level',  # Battery sensors
    'sensor.*_battery_state',  # Battery state
    'sensor.*_status',         # Status sensors
    'sensor.*_tracker',        # Tracker sensors
    'sensor.*_distance',       # Distance sensors
    'sensor.*_steps',          # Fitness sensors
    'event.',                  # All events
    'image.',                  # All images
]

# Minimum requirements for pattern quality
MIN_OCCURRENCES = 10  # Minimum occurrences for a valid pattern
MIN_CONFIDENCE = 0.7  # Minimum confidence threshold


def is_actionable_device(device_id: str) -> bool:
    """
    Check if a device is actionable for automation.
    
    Args:
        device_id: Device entity ID (e.g., "light.bedroom", "sensor.battery")
        
    Returns:
        True if device is actionable, False otherwise
    """
    if not device_id or '.' not in device_id:
        return False
    
    domain = device_id.split('.')[0]
    
    # Check excluded domains
    if domain in EXCLUDED_DOMAINS:
        return False
    
    # Check excluded prefixes
    for prefix in EXCLUDED_PREFIXES:
        if prefix.endswith('*'):
            # Handle wildcard patterns
            prefix_base = prefix.replace('*', '')
            if prefix_base in device_id:
                return False
        elif device_id.startswith(prefix):
            return False
    
    # Check if it's an actionable domain
    if domain in ACTIONABLE_DOMAINS:
        return True
    
    # Default: allow if not explicitly excluded
    return True


def validate_pattern(pattern: dict) -> bool:
    """
    Validate pattern meets quality requirements.
    
    Args:
        pattern: Pattern dictionary with keys: device_id, occurrences, confidence
                For co-occurrence patterns, also has device1 and device2 keys
        
    Returns:
        True if pattern is valid, False otherwise
    """
    pattern_type = pattern.get('pattern_type', '')
    
    # For co-occurrence patterns, check BOTH devices
    if pattern_type == 'co_occurrence':
        device1 = pattern.get('device1', '')
        device2 = pattern.get('device2', '')
        
        # Both devices must be actionable for co-occurrence patterns
        if not device1 or not device2:
            return False
        
        if not is_actionable_device(device1) or not is_actionable_device(device2):
            return False
    else:
        # For other patterns, check the device_id
        device_id = pattern.get('device_id', '')
        if not is_actionable_device(device_id):
            return False
    
    # Check minimum occurrences
    occurrences = pattern.get('occurrences', 0)
    if occurrences < MIN_OCCURRENCES:
        return False
    
    # Check minimum confidence
    confidence = pattern.get('confidence', 0.0)
    if confidence < MIN_CONFIDENCE:
        return False
    
    return True

