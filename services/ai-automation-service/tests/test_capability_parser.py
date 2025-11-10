"""
Unit Tests for CapabilityParser (Epic AI-2, Story AI2.1)

Tests universal parsing of Zigbee2MQTT 'exposes' format for all manufacturers.
"""

import pytest
from src.device_intelligence.capability_parser import CapabilityParser


class TestCapabilityParser:
    """Test CapabilityParser universal device capability parsing"""
    
    def setup_method(self):
        """Initialize parser for each test"""
        self.parser = CapabilityParser()
    
    # =========================================================================
    # Inovelli Device Tests (Switch/Dimmer)
    # =========================================================================
    
    def test_parse_inovelli_switch(self):
        """Test parsing Inovelli VZM31-SN switch exposes"""
        exposes = [
            {"type": "light", "features": [{"name": "state"}, {"name": "brightness"}]},
            {"type": "enum", "name": "smartBulbMode", "values": ["Disabled", "Enabled"], "description": "Smart bulb mode"},
            {"type": "numeric", "name": "autoTimerOff", "value_min": 0, "value_max": 32767, "unit": "seconds"}
        ]
        
        capabilities = self.parser.parse_exposes(exposes)
        
        # Should have 3 capabilities
        assert len(capabilities) == 3
        
        # Check light control
        assert "light_control" in capabilities
        assert capabilities["light_control"]["type"] == "composite"
        assert "state" in capabilities["light_control"]["features"]
        assert "brightness" in capabilities["light_control"]["features"]
        
        # Check smart bulb mode (enum)
        assert "smart_bulb_mode" in capabilities
        assert capabilities["smart_bulb_mode"]["type"] == "enum"
        assert capabilities["smart_bulb_mode"]["mqtt_name"] == "smartBulbMode"
        assert "Enabled" in capabilities["smart_bulb_mode"]["values"]
        
        # Check auto timer off (numeric)
        assert "auto_off_timer" in capabilities
        assert capabilities["auto_off_timer"]["type"] == "numeric"
        assert capabilities["auto_off_timer"]["min"] == 0
        assert capabilities["auto_off_timer"]["max"] == 32767
    
    # =========================================================================
    # Aqara Device Tests (Sensors)
    # =========================================================================
    
    def test_parse_aqara_contact_sensor(self):
        """Test parsing Aqara MCCGQ11LM contact sensor exposes"""
        exposes = [
            {"type": "binary", "name": "contact", "value_on": "open", "value_off": "close", "description": "Door/window contact"},
            {"type": "binary", "name": "vibration", "value_on": True, "value_off": False, "description": "Vibration detected"},
            {"type": "numeric", "name": "battery", "unit": "%", "value_min": 0, "value_max": 100}
        ]
        
        capabilities = self.parser.parse_exposes(exposes)
        
        # Should have 3 capabilities
        assert len(capabilities) == 3
        
        # Check contact sensor
        assert "contact" in capabilities
        assert capabilities["contact"]["type"] == "binary"
        assert capabilities["contact"]["value_on"] == "open"
        assert capabilities["contact"]["value_off"] == "close"
        
        # Check vibration sensor
        assert "vibration" in capabilities
        assert capabilities["vibration"]["type"] == "binary"
        
        # Check battery
        assert "battery" in capabilities
        assert capabilities["battery"]["unit"] == "%"
    
    # =========================================================================
    # IKEA Device Tests (Bulbs)
    # =========================================================================
    
    def test_parse_ikea_bulb(self):
        """Test parsing IKEA LED1624G9 bulb exposes"""
        exposes = [
            {
                "type": "light",
                "features": [
                    {"name": "state"},
                    {"name": "brightness"},
                    {"name": "color_temp"}
                ]
            },
            {"type": "enum", "name": "effect", "values": ["blink", "breathe", "okay", "finish_effect"]}
        ]
        
        capabilities = self.parser.parse_exposes(exposes)
        
        # Should have 2 capabilities
        assert len(capabilities) == 2
        
        # Check light control with color temp
        assert "light_control" in capabilities
        assert "color_temp" in capabilities["light_control"]["features"]
        
        # Check effect (advanced feature)
        assert "effect" in capabilities
        assert capabilities["effect"]["complexity"] == "advanced"  # Effect is advanced
    
    # =========================================================================
    # Xiaomi Device Tests (Sensors)
    # =========================================================================
    
    def test_parse_xiaomi_temperature_sensor(self):
        """Test parsing Xiaomi WSDCGQ11LM temperature/humidity sensor"""
        exposes = [
            {"type": "numeric", "name": "temperature", "unit": "°C", "value_min": -40, "value_max": 125},
            {"type": "numeric", "name": "humidity", "unit": "%", "value_min": 0, "value_max": 100},
            {"type": "numeric", "name": "battery", "unit": "%", "value_min": 0, "value_max": 100}
        ]
        
        capabilities = self.parser.parse_exposes(exposes)
        
        # Should have 3 capabilities
        assert len(capabilities) == 3
        
        assert "temperature" in capabilities
        assert capabilities["temperature"]["unit"] == "°C"
        
        assert "humidity" in capabilities
        assert capabilities["humidity"]["unit"] == "%"
        
        assert "battery" in capabilities
    
    # =========================================================================
    # Edge Cases and Error Handling
    # =========================================================================
    
    def test_parse_unknown_expose_type(self):
        """Test parser doesn't crash on unknown expose type"""
        exposes = [
            {"type": "unknown_future_type", "name": "future_feature"}
        ]
        
        # Should not crash
        capabilities = self.parser.parse_exposes(exposes)
        assert isinstance(capabilities, dict)
        # Unknown type should be skipped
        assert len(capabilities) == 0
    
    def test_parse_empty_exposes(self):
        """Test parser handles empty exposes array"""
        capabilities = self.parser.parse_exposes([])
        
        assert isinstance(capabilities, dict)
        assert len(capabilities) == 0
    
    def test_parse_malformed_expose(self):
        """Test parser handles malformed expose objects"""
        exposes = [
            {"type": "enum"},  # Missing 'name'
            {"name": "something"},  # Missing 'type'
            "not a dict",  # Not a dict
            None  # None
        ]
        
        # Should not crash
        capabilities = self.parser.parse_exposes(exposes)
        assert isinstance(capabilities, dict)
    
    def test_parse_expose_without_name(self):
        """Test enum/numeric/binary exposes without 'name' field"""
        exposes = [
            {"type": "enum", "values": ["a", "b"]},  # Missing name
            {"type": "numeric", "value_min": 0},  # Missing name
            {"type": "binary", "value_on": True}  # Missing name
        ]
        
        capabilities = self.parser.parse_exposes(exposes)
        
        # Should skip exposes without names
        assert len(capabilities) == 0
    
    # =========================================================================
    # Name Mapping Tests
    # =========================================================================
    
    def test_mqtt_to_friendly_name_mapping(self):
        """Test MQTT name to friendly name conversion"""
        test_cases = [
            ("smartBulbMode", "smart_bulb_mode"),
            ("autoTimerOff", "auto_off_timer"),
            ("led_effect", "led_notifications"),
            ("LEDWhenOn", "led_when_on"),
            ("powerOnBehavior", "power_on_behavior"),
            ("unknownName", "unknown_name"),  # No mapping, camelCase converted to snake_case
        ]
        
        for mqtt_name, expected_friendly in test_cases:
            result = self.parser._map_mqtt_to_friendly(mqtt_name)
            assert result == expected_friendly, f"Expected {expected_friendly}, got {result}"
    
    # =========================================================================
    # Complexity Assessment Tests
    # =========================================================================
    
    def test_assess_complexity(self):
        """Test feature complexity assessment"""
        # Advanced features
        assert self.parser._assess_complexity("led_effect") == "advanced"
        assert self.parser._assess_complexity("transition_time") == "advanced"
        assert self.parser._assess_complexity("calibration_offset") == "advanced"
        
        # Medium complexity features
        assert self.parser._assess_complexity("autoTimerOff") == "medium"
        assert self.parser._assess_complexity("delay_seconds") == "medium"
        assert self.parser._assess_complexity("threshold_value") == "medium"
        
        # Easy features (default)
        assert self.parser._assess_complexity("smartBulbMode") == "easy"
        assert self.parser._assess_complexity("power_on_behavior") == "easy"
    
    # =========================================================================
    # Climate Control Tests
    # =========================================================================
    
    def test_parse_climate_control(self):
        """Test parsing thermostat/climate control exposes"""
        exposes = [
            {
                "type": "climate",
                "features": [
                    {"name": "current_heating_setpoint"},
                    {"name": "local_temperature"},
                    {"name": "system_mode"}
                ]
            }
        ]
        
        capabilities = self.parser.parse_exposes(exposes)
        
        assert "climate_control" in capabilities
        assert capabilities["climate_control"]["type"] == "composite"
        assert capabilities["climate_control"]["complexity"] == "medium"
        assert len(capabilities["climate_control"]["features"]) == 3
    
    # =========================================================================
    # Switch Control Tests
    # =========================================================================
    
    def test_parse_switch_control(self):
        """Test parsing basic switch exposes"""
        exposes = [
            {"type": "switch"}
        ]
        
        capabilities = self.parser.parse_exposes(exposes)
        
        assert "switch_control" in capabilities
        assert capabilities["switch_control"]["type"] == "binary"
        assert capabilities["switch_control"]["complexity"] == "easy"
    
    # =========================================================================
    # Multi-Manufacturer Integration Test
    # =========================================================================
    
    @pytest.mark.parametrize("manufacturer,exposes,expected_count", [
        ("Inovelli", [
            {"type": "light", "features": [{"name": "state"}]},
            {"type": "enum", "name": "smartBulbMode", "values": ["Disabled", "Enabled"]}
        ], 2),
        ("Aqara", [
            {"type": "binary", "name": "contact", "value_on": "open", "value_off": "close"}
        ], 1),
        ("IKEA", [
            {"type": "light", "features": [{"name": "state"}, {"name": "brightness"}]}
        ], 1),
        ("Xiaomi", [
            {"type": "numeric", "name": "temperature", "unit": "°C"}
        ], 1),
    ])
    def test_parse_multiple_manufacturers(self, manufacturer, exposes, expected_count):
        """Test parser works for multiple manufacturers"""
        capabilities = self.parser.parse_exposes(exposes)
        
        assert len(capabilities) == expected_count
        assert isinstance(capabilities, dict)
        
        # All capabilities should have required fields
        for cap_name, cap_data in capabilities.items():
            assert "type" in cap_data
            assert "complexity" in cap_data

