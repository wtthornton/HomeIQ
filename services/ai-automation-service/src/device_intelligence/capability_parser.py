"""
Universal Capability Parser for Zigbee2MQTT Device Definitions

Parses the standardized Zigbee2MQTT 'exposes' format into structured capability data.
Works for ALL Zigbee manufacturers: Inovelli, Aqara, IKEA, Xiaomi, Sonoff, Tuya, and 100+ more.

Story: AI2.1 - MQTT Capability Listener & Universal Parser
Epic: AI-2 - Device Intelligence System
"""

import logging

logger = logging.getLogger(__name__)


class CapabilityParser:
    """
    Universal parser for Zigbee2MQTT 'exposes' format.
    
    Parses device capability definitions from Zigbee2MQTT bridge messages
    and converts them into a structured format for storage and analysis.
    
    Supports:
    - Light control (brightness, color, color temperature)
    - Switch control (on/off)
    - Climate control (thermostats, HVAC)
    - Binary sensors (contact, motion, vibration)
    - Enum configuration options
    - Numeric configuration options
    
    Example Usage:
        parser = CapabilityParser()
        capabilities = parser.parse_exposes(zigbee2mqtt_exposes)
        # Returns: {"light_control": {...}, "smart_bulb_mode": {...}, ...}
    """

    def parse_exposes(self, exposes: list[dict]) -> dict[str, dict]:
        """
        Parse Zigbee2MQTT exposes array into structured capabilities.
        
        Args:
            exposes: List of expose objects from Zigbee2MQTT device definition
            
        Returns:
            Dict of capabilities: {capability_name: {type, mqtt_name, description, ...}}
            
        Example Input (Inovelli VZM31-SN):
            [
                {"type": "light", "features": [{"name": "state"}, {"name": "brightness"}]},
                {"type": "enum", "name": "smartBulbMode", "values": ["Disabled", "Enabled"]},
                {"type": "numeric", "name": "autoTimerOff", "value_min": 0, "value_max": 32767}
            ]
            
        Example Output:
            {
                "light_control": {
                    "type": "composite",
                    "mqtt_name": "light",
                    "description": "Basic light control",
                    "complexity": "easy",
                    "features": ["state", "brightness"]
                },
                "smart_bulb_mode": {
                    "type": "enum",
                    "mqtt_name": "smartBulbMode",
                    "values": ["Disabled", "Enabled"],
                    "description": "",
                    "complexity": "easy"
                },
                "auto_off_timer": {
                    "type": "numeric",
                    "mqtt_name": "autoTimerOff",
                    "min": 0,
                    "max": 32767,
                    "unit": "",
                    "description": "",
                    "complexity": "medium"
                }
            }
        """
        if not exposes:
            logger.debug("Empty exposes array")
            return {}

        capabilities = {}

        for expose in exposes:
            if not isinstance(expose, dict):
                logger.warning(f"Invalid expose format (not a dict): {type(expose)}")
                continue

            expose_type = expose.get('type')

            if not expose_type:
                logger.debug("Expose missing 'type' field, skipping")
                continue

            # Handle different expose types
            try:
                if expose_type == 'light':
                    capabilities.update(self._parse_light_control(expose))
                elif expose_type == 'switch':
                    capabilities.update(self._parse_switch_control(expose))
                elif expose_type == 'climate':
                    capabilities.update(self._parse_climate_control(expose))
                elif expose_type == 'enum':
                    capability = self._parse_enum_option(expose)
                    if capability:
                        capabilities.update(capability)
                elif expose_type == 'numeric':
                    capability = self._parse_numeric_option(expose)
                    if capability:
                        capabilities.update(capability)
                elif expose_type == 'binary':
                    capability = self._parse_binary_option(expose)
                    if capability:
                        capabilities.update(capability)
                else:
                    # Unknown type - log and continue (future-proof)
                    logger.debug(f"Unknown expose type '{expose_type}', skipping")

            except Exception as e:
                logger.warning(f"Error parsing expose type '{expose_type}': {e}")
                continue

        return capabilities

    def _parse_light_control(self, expose: dict) -> dict[str, dict]:
        """
        Parse light control expose (state, brightness, color, color temperature).
        
        Args:
            expose: Light expose object from Zigbee2MQTT
            
        Returns:
            Dict with "light_control" capability
        """
        features = expose.get('features', [])

        capability = {
            "light_control": {
                "type": "composite",
                "mqtt_name": "light",
                "description": expose.get('description', 'Basic light control'),
                "complexity": "easy",
                "features": []
            }
        }

        # Parse sub-features (state, brightness, color_temp, color_xy, etc.)
        for feature in features:
            if isinstance(feature, dict):
                feature_name = feature.get('name')
                if feature_name:
                    capability["light_control"]["features"].append(feature_name)

        # Assess complexity based on features
        if 'color_xy' in capability["light_control"]["features"] or 'color_hs' in capability["light_control"]["features"]:
            capability["light_control"]["complexity"] = "medium"

        return capability

    def _parse_switch_control(self, expose: dict) -> dict[str, dict]:
        """
        Parse switch control expose (basic on/off).
        
        Args:
            expose: Switch expose object from Zigbee2MQTT
            
        Returns:
            Dict with "switch_control" capability
        """
        return {
            "switch_control": {
                "type": "binary",
                "mqtt_name": "switch",
                "description": expose.get('description', 'Basic switch on/off'),
                "complexity": "easy"
            }
        }

    def _parse_climate_control(self, expose: dict) -> dict[str, dict]:
        """
        Parse climate/thermostat control expose.
        
        Args:
            expose: Climate expose object from Zigbee2MQTT
            
        Returns:
            Dict with "climate_control" capability
        """
        features = expose.get('features', [])

        feature_names = []
        for feature in features:
            if isinstance(feature, dict):
                feature_name = feature.get('name')
                if feature_name:
                    feature_names.append(feature_name)

        return {
            "climate_control": {
                "type": "composite",
                "mqtt_name": "climate",
                "description": expose.get('description', 'Temperature and climate control'),
                "complexity": "medium",
                "features": feature_names
            }
        }

    def _parse_enum_option(self, expose: dict) -> dict[str, dict] | None:
        """
        Parse enum configuration option (e.g., smartBulbMode, ledEffect).
        
        Args:
            expose: Enum expose object from Zigbee2MQTT
            
        Returns:
            Dict with single capability, or None if name missing
        """
        mqtt_name = expose.get('name')
        if not mqtt_name:
            logger.debug("Enum expose missing 'name' field")
            return None

        friendly_name = self._map_mqtt_to_friendly(mqtt_name)
        values = expose.get('values', [])
        description = expose.get('description', '')

        return {
            friendly_name: {
                "type": "enum",
                "mqtt_name": mqtt_name,
                "values": values,
                "description": description,
                "complexity": self._assess_complexity(mqtt_name)
            }
        }

    def _parse_numeric_option(self, expose: dict) -> dict[str, dict] | None:
        """
        Parse numeric configuration option (e.g., autoTimerOff, brightness).
        
        Args:
            expose: Numeric expose object from Zigbee2MQTT
            
        Returns:
            Dict with single capability, or None if name missing
        """
        mqtt_name = expose.get('name')
        if not mqtt_name:
            logger.debug("Numeric expose missing 'name' field")
            return None

        friendly_name = self._map_mqtt_to_friendly(mqtt_name)

        return {
            friendly_name: {
                "type": "numeric",
                "mqtt_name": mqtt_name,
                "min": expose.get('value_min'),
                "max": expose.get('value_max'),
                "unit": expose.get('unit', ''),
                "description": expose.get('description', ''),
                "complexity": self._assess_complexity(mqtt_name)
            }
        }

    def _parse_binary_option(self, expose: dict) -> dict[str, dict] | None:
        """
        Parse binary option (e.g., contact sensor, motion, vibration).
        
        Args:
            expose: Binary expose object from Zigbee2MQTT
            
        Returns:
            Dict with single capability, or None if name missing
        """
        mqtt_name = expose.get('name')
        if not mqtt_name:
            logger.debug("Binary expose missing 'name' field")
            return None

        friendly_name = self._map_mqtt_to_friendly(mqtt_name)

        return {
            friendly_name: {
                "type": "binary",
                "mqtt_name": mqtt_name,
                "value_on": expose.get('value_on'),
                "value_off": expose.get('value_off'),
                "description": expose.get('description', ''),
                "complexity": "easy"
            }
        }

    def _map_mqtt_to_friendly(self, mqtt_name: str) -> str:
        """
        Map MQTT names to user-friendly names.
        
        Converts camelCase and kebab-case to snake_case for consistency.
        
        Args:
            mqtt_name: Original MQTT name (e.g., "smartBulbMode")
            
        Returns:
            Friendly name (e.g., "smart_bulb_mode")
            
        Examples:
            smartBulbMode -> smart_bulb_mode
            autoTimerOff -> auto_off_timer
            led_effect -> led_notifications
            LEDWhenOn -> led_when_on
        """
        # Known mappings (manufacturer-specific or common)
        mapping = {
            'smartBulbMode': 'smart_bulb_mode',
            'autoTimerOff': 'auto_off_timer',
            'led_effect': 'led_notifications',
            'ledEffect': 'led_notifications',
            'ledWhenOn': 'led_when_on',
            'ledWhenOff': 'led_when_off',
            'LEDWhenOn': 'led_when_on',
            'LEDWhenOff': 'led_when_off',
            'powerOnBehavior': 'power_on_behavior',
            'localProtection': 'local_protection',
            'remoteProtection': 'remote_protection',
        }

        # Check mapping first
        if mqtt_name in mapping:
            return mapping[mqtt_name]

        # Convert camelCase to snake_case
        result = []
        for i, char in enumerate(mqtt_name):
            if char.isupper() and i > 0:
                # Add underscore before uppercase if previous char was lowercase
                if mqtt_name[i-1].islower():
                    result.append('_')
            result.append(char.lower())

        snake_case = ''.join(result)

        # Replace spaces and hyphens with underscores
        snake_case = snake_case.replace(' ', '_').replace('-', '_')

        # Remove duplicate underscores
        while '__' in snake_case:
            snake_case = snake_case.replace('__', '_')

        return snake_case

    def _assess_complexity(self, mqtt_name: str) -> str:
        """
        Assess complexity of feature configuration.
        
        Returns complexity level based on feature name heuristics.
        
        Args:
            mqtt_name: MQTT name of the feature
            
        Returns:
            "easy" | "medium" | "advanced"
            
        Heuristics:
            - Advanced: effect, transition, calibration, sensitivity
            - Medium: timer, delay, threshold, duration
            - Easy: everything else
        """
        # Keywords indicating complexity
        advanced_keywords = ['effect', 'transition', 'calibration', 'sensitivity', 'advanced', 'scene']
        medium_keywords = ['timer', 'delay', 'threshold', 'duration', 'interval', 'timeout']

        name_lower = mqtt_name.lower()

        # Check for advanced features
        if any(kw in name_lower for kw in advanced_keywords):
            return "advanced"

        # Check for medium complexity features
        if any(kw in name_lower for kw in medium_keywords):
            return "medium"

        # Default to easy
        return "easy"

