"""
Bitmask Capability Parser

Parses Home Assistant entity capabilities using the supported_features bitmask.
This replaces hardcoded elif chains with a data-driven approach using HA constants.
"""

import logging
from typing import Any

from .constants import LightEntityFeature
from .feature_mapper import generate_friendly_capabilities

logger = logging.getLogger(__name__)


class BitmaskCapabilityParser:
    """
    Parse HA entity capabilities from supported_features bitmask.
    
    Replaces hardcoded elif chains with a data-driven approach.
    Uses Home Assistant's official feature constants for accuracy.
    """

    def __init__(self):
        """Initialize the parser with domain constants."""
        self.domain_constants = {
            'light': LightEntityFeature,
        }

    def parse_capabilities(
        self,
        domain: str,
        supported_features: int,
        attributes: dict | None = None
    ) -> dict[str, Any]:
        """
        Parse supported_features bitmask into structured capabilities.
        
        Args:
            domain: Entity domain (light, climate, cover, etc.)
            supported_features: Bitmask value from entity attributes
            attributes: Entity attributes for additional context
            
        Returns:
            Dictionary with supported_features and friendly_capabilities
            
        Example:
            >>> parser = BitmaskCapabilityParser()
            >>> caps = parser.parse_capabilities('light', 147)
            >>> caps['supported_features']['brightness']  # True
            >>> caps['supported_features']['color_temp']  # True
        """
        features = self._parse_supported_features(domain, supported_features)

        return {
            'supported_features': features,
            'friendly_capabilities': generate_friendly_capabilities(domain, features)
        }

    def _parse_supported_features(self, domain: str, bitmask: int) -> dict[str, bool]:
        """
        Parse bitmask into feature flags using domain constants.
        
        Args:
            domain: Entity domain
            bitmask: Bitmask value from supported_features
            
        Returns:
            Dictionary of feature names to boolean values
        """
        if domain == 'light':
            return self._parse_light_features(bitmask)
        elif domain == 'climate':
            return self._parse_climate_features(bitmask)
        elif domain == 'cover':
            return self._parse_cover_features(bitmask)
        elif domain == 'fan':
            return self._parse_fan_features(bitmask)
        else:
            # Generic fallback for unknown domains
            logger.debug(f"Unknown domain '{domain}', using generic capabilities")
            return {'on_off': True}

    def _parse_light_features(self, bitmask: int) -> dict[str, bool]:
        """Parse light entity features from bitmask."""
        return {
            'brightness': bool(bitmask & LightEntityFeature.SUPPORT_BRIGHTNESS),
            'color_temp': bool(bitmask & LightEntityFeature.SUPPORT_COLOR_TEMP),
            'effect': bool(bitmask & LightEntityFeature.SUPPORT_EFFECT),
            'flash': bool(bitmask & LightEntityFeature.SUPPORT_FLASH),
            'rgb_color': bool(bitmask & LightEntityFeature.SUPPORT_COLOR),
            'transition': bool(bitmask & LightEntityFeature.SUPPORT_TRANSITION),
            'white_value': bool(bitmask & LightEntityFeature.SUPPORT_WHITE_VALUE),
        }

    def _parse_climate_features(self, bitmask: int) -> dict[str, bool]:
        """Parse climate entity features from bitmask."""
        from .constants import ClimateEntityFeature

        return {
            'temperature': bool(bitmask & ClimateEntityFeature.SUPPORT_TARGET_TEMPERATURE),
            'temperature_range': bool(bitmask & ClimateEntityFeature.SUPPORT_TARGET_TEMPERATURE_RANGE),
            'humidity': bool(bitmask & ClimateEntityFeature.SUPPORT_TARGET_HUMIDITY),
            'fan_mode': bool(bitmask & ClimateEntityFeature.SUPPORT_FAN_MODE),
            'preset': bool(bitmask & ClimateEntityFeature.SUPPORT_PRESET_MODE),
            'swing_mode': bool(bitmask & ClimateEntityFeature.SUPPORT_SWING_MODE),
            'aux_heat': bool(bitmask & ClimateEntityFeature.SUPPORT_AUX_HEAT),
        }

    def _parse_cover_features(self, bitmask: int) -> dict[str, bool]:
        """Parse cover entity features from bitmask."""
        from .constants import CoverEntityFeature

        return {
            'open': bool(bitmask & CoverEntityFeature.SUPPORT_OPEN),
            'close': bool(bitmask & CoverEntityFeature.SUPPORT_CLOSE),
            'position': bool(bitmask & CoverEntityFeature.SUPPORT_SET_POSITION),
            'stop': bool(bitmask & CoverEntityFeature.SUPPORT_STOP),
            'tilt_open': bool(bitmask & CoverEntityFeature.SUPPORT_OPEN_TILT),
            'tilt_close': bool(bitmask & CoverEntityFeature.SUPPORT_CLOSE_TILT),
            'tilt_position': bool(bitmask & CoverEntityFeature.SUPPORT_SET_TILT_POSITION),
        }

    def _parse_fan_features(self, bitmask: int) -> dict[str, bool]:
        """Parse fan entity features from bitmask."""
        from .constants import FanEntityFeature

        return {
            'speed': bool(bitmask & FanEntityFeature.SUPPORT_SET_SPEED),
            'direction': bool(bitmask & FanEntityFeature.SUPPORT_DIRECTION),
            'oscillate': bool(bitmask & FanEntityFeature.SUPPORT_OSCILLATE),
            'preset': bool(bitmask & FanEntityFeature.SUPPORT_PRESET_MODE),
            'increase_speed': bool(bitmask & FanEntityFeature.SUPPORT_INCREASE_SPEED),
            'decrease_speed': bool(bitmask & FanEntityFeature.SUPPORT_DECREASE_SPEED),
        }

