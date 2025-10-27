"""
Home Assistant supported_features Bitmask Constants.

Note: In production, these would be imported from homeassistant.components.*
For now, we define them manually to avoid the heavy HA dependency.
"""

from typing import Dict, Any

# LightEntityFeature constants (from homeassistant.components.light)
class LightEntityFeature:
    """Light entity feature flags."""
    SUPPORT_BRIGHTNESS = 1      # Bit 0
    SUPPORT_COLOR_TEMP = 2     # Bit 1
    SUPPORT_EFFECT = 4         # Bit 2
    SUPPORT_FLASH = 8          # Bit 3
    SUPPORT_COLOR = 16         # Bit 4
    SUPPORT_TRANSITION = 32    # Bit 5
    SUPPORT_WHITE_VALUE = 128  # Bit 7

# ClimateEntityFeature constants
class ClimateEntityFeature:
    """Climate entity feature flags."""
    SUPPORT_TARGET_TEMPERATURE = 1      # Bit 0
    SUPPORT_TARGET_TEMPERATURE_RANGE = 2  # Bit 1
    SUPPORT_TARGET_HUMIDITY = 4         # Bit 2
    SUPPORT_FAN_MODE = 8                # Bit 3
    SUPPORT_PRESET_MODE = 16            # Bit 4
    SUPPORT_SWING_MODE = 32             # Bit 5
    SUPPORT_AUX_HEAT = 64               # Bit 6
    SUPPORT_TURN_ON = 128               # Bit 7
    SUPPORT_TURN_OFF = 256              # Bit 8

# CoverEntityFeature constants
class CoverEntityFeature:
    """Cover entity feature flags."""
    SUPPORT_OPEN = 1        # Bit 0
    SUPPORT_CLOSE = 2       # Bit 1
    SUPPORT_SET_POSITION = 4   # Bit 2
    SUPPORT_STOP = 8        # Bit 3
    SUPPORT_OPEN_TILT = 16  # Bit 4
    SUPPORT_CLOSE_TILT = 32 # Bit 5
    SUPPORT_SET_TILT_POSITION = 64  # Bit 6

# FanEntityFeature constants
class FanEntityFeature:
    """Fan entity feature flags."""
    SUPPORT_SET_SPEED = 1         # Bit 0
    SUPPORT_DIRECTION = 2          # Bit 1
    SUPPORT_OSCILLATE = 4          # Bit 2
    SUPPORT_PRESET_MODE = 8        # Bit 3
    SUPPORT_INCREASE_SPEED = 16    # Bit 4
    SUPPORT_DECREASE_SPEED = 32    # Bit 5

# Mapping domain to its feature constants
DOMAIN_CONSTANTS: Dict[str, Any] = {
    'light': LightEntityFeature,
    'climate': ClimateEntityFeature,
    'cover': CoverEntityFeature,
    'fan': FanEntityFeature,
}


def get_domain_constants(domain: str):
    """Get feature constants for a domain."""
    return DOMAIN_CONSTANTS.get(domain)

