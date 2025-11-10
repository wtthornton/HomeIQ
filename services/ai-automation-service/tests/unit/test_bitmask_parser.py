"""
Unit tests for BitmaskCapabilityParser.

Tests the new bitmask-based capability parsing that replaces hardcoded elif chains.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from clients.capability_parsers.bitmask_parser import BitmaskCapabilityParser
from clients.capability_parsers.constants import LightEntityFeature, ClimateEntityFeature, CoverEntityFeature, FanEntityFeature


class TestBitmaskCapabilityParser:
    """Test suite for BitmaskCapabilityParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = BitmaskCapabilityParser()
    
    def test_parse_light_features_full_support(self):
        """Test parsing light with all features enabled (bitmask 255)."""
        # Full support: all bits set
        bitmask = 255  # All features
        
        features = self.parser._parse_light_features(bitmask)
        
        assert features['brightness'] is True
        assert features['color_temp'] is True
        assert features['effect'] is True
        assert features['flash'] is True
        assert features['rgb_color'] is True
        assert features['transition'] is True
        assert features['white_value'] is True
    
    def test_parse_light_features_minimal(self):
        """Test parsing light with minimal features (bitmask 1)."""
        # Only brightness support
        bitmask = LightEntityFeature.SUPPORT_BRIGHTNESS  # 1
        
        features = self.parser._parse_light_features(bitmask)
        
        assert features['brightness'] is True
        assert features['color_temp'] is False
        assert features['rgb_color'] is False
        assert features['flash'] is False
    
    def test_parse_light_features_common(self):
        """Test parsing light with common features (brightness + color + transition)."""
        # Typical smart bulb: brightness, RGB color, transition
        bitmask = (
            LightEntityFeature.SUPPORT_BRIGHTNESS |
            LightEntityFeature.SUPPORT_COLOR |
            LightEntityFeature.SUPPORT_TRANSITION
        )  # 1 + 16 + 32 = 49
        
        features = self.parser._parse_light_features(bitmask)
        
        assert features['brightness'] is True
        assert features['rgb_color'] is True
        assert features['transition'] is True
        assert features['color_temp'] is False
        assert features['flash'] is False
    
    def test_parse_climate_features(self):
        """Test parsing climate entity features."""
        bitmask = (
            ClimateEntityFeature.SUPPORT_TARGET_TEMPERATURE |
            ClimateEntityFeature.SUPPORT_FAN_MODE |
            ClimateEntityFeature.SUPPORT_PRESET_MODE
        )
        
        features = self.parser._parse_climate_features(bitmask)
        
        assert features['temperature'] is True
        assert features['fan_mode'] is True
        assert features['preset'] is True
        assert features['humidity'] is False
    
    def test_parse_cover_features(self):
        """Test parsing cover entity features."""
        bitmask = (
            CoverEntityFeature.SUPPORT_OPEN |
            CoverEntityFeature.SUPPORT_CLOSE |
            CoverEntityFeature.SUPPORT_SET_POSITION
        )
        
        features = self.parser._parse_cover_features(bitmask)
        
        assert features['open'] is True
        assert features['close'] is True
        assert features['position'] is True
        assert features['tilt_open'] is False
    
    def test_parse_fan_features(self):
        """Test parsing fan entity features."""
        bitmask = (
            FanEntityFeature.SUPPORT_SET_SPEED |
            FanEntityFeature.SUPPORT_DIRECTION |
            FanEntityFeature.SUPPORT_OSCILLATE
        )
        
        features = self.parser._parse_fan_features(bitmask)
        
        assert features['speed'] is True
        assert features['direction'] is True
        assert features['oscillate'] is True
        assert features['preset'] is False
    
    def test_parse_capabilities_integration(self):
        """Test full parse_capabilities integration."""
        # Real-world example: Philips Hue bulb
        result = self.parser.parse_capabilities(
            domain='light',
            supported_features=147,  # brightness, color_temp, color, transition
            attributes={
                'brightness': 128,
                'rgb_color': [255, 0, 0]
            }
        )
        
        assert 'supported_features' in result
        assert 'friendly_capabilities' in result
        assert result['supported_features']['brightness'] is True
        assert result['supported_features']['rgb_color'] is True
        assert len(result['friendly_capabilities']) > 0
    
    def test_unknown_domain_fallback(self):
        """Test fallback for unknown domains."""
        result = self.parser.parse_capabilities(
            domain='unknown_domain',
            supported_features=0
        )
        
        assert result['supported_features'] == {'on_off': True}
        assert len(result['friendly_capabilities']) > 0
    
    def test_empty_bitmask(self):
        """Test handling of empty bitmask (no features)."""
        result = self.parser._parse_light_features(0)
        
        # All features should be False
        assert all(not value for value in result.values())
    
    def test_friendly_capabilities_generation(self):
        """Test that friendly capabilities are generated."""
        result = self.parser.parse_capabilities(
            domain='light',
            supported_features=(
                LightEntityFeature.SUPPORT_BRIGHTNESS |
                LightEntityFeature.SUPPORT_COLOR
            )
        )
        
        friendly_caps = result['friendly_capabilities']
        
        assert len(friendly_caps) >= 2
        assert any('brightness' in cap.lower() for cap in friendly_caps)
        assert any('color' in cap.lower() for cap in friendly_caps)


class TestRealWorldScenarios:
    """Test real-world entity scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = BitmaskCapabilityParser()
    
    def test_ikea_tradfri_bulb(self):
        """Test parsing capabilities for IKEA TRADFRI bulb (brightness only)."""
        # Typically: only brightness support
        bitmask = LightEntityFeature.SUPPORT_BRIGHTNESS
        features = self.parser._parse_light_features(bitmask)
        
        assert features['brightness'] is True
        assert features['rgb_color'] is False
    
    def test_philips_hue_color(self):
        """Test parsing capabilities for Philips Hue Color (full features)."""
        # Typically: brightness, RGB, color temp, effects
        bitmask = (
            LightEntityFeature.SUPPORT_BRIGHTNESS |
            LightEntityFeature.SUPPORT_COLOR |
            LightEntityFeature.SUPPORT_COLOR_TEMP |
            LightEntityFeature.SUPPORT_EFFECT |
            LightEntityFeature.SUPPORT_TRANSITION
        )
        features = self.parser._parse_light_features(bitmask)
        
        assert features['brightness'] is True
        assert features['rgb_color'] is True
        assert features['color_temp'] is True
        assert features['effect'] is True
        assert features['transition'] is True
    
    def test_nest_thermostat(self):
        """Test parsing capabilities for Nest thermostat."""
        # Typically: temperature, fan mode, preset
        bitmask = (
            ClimateEntityFeature.SUPPORT_TARGET_TEMPERATURE |
            ClimateEntityFeature.SUPPORT_FAN_MODE |
            ClimateEntityFeature.SUPPORT_PRESET_MODE
        )
        features = self.parser._parse_climate_features(bitmask)
        
        assert features['temperature'] is True
        assert features['fan_mode'] is True
        assert features['preset'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

