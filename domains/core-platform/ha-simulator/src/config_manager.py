"""
Configuration Manager for HA Simulator

Handles loading and managing configuration from YAML files and environment variables.
"""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration for the HA Simulator"""

    def __init__(self, config_path: str = "config/simulator-config.yaml"):
        self.config_path = config_path
        self.config: dict[str, Any] = {}
        self.load_config()

    def load_config(self):
        """Load configuration from file and environment"""
        # Load base configuration
        if Path(self.config_path).exists():
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
        else:
            self.config = self._get_default_config()
            logger.info("Using default configuration")

        # Override with environment variables
        self._apply_environment_overrides()

        # Validate configuration
        self._validate_config()

        logger.info("Configuration loaded successfully")

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration"""
        return {
            "simulator": {
                "name": "HA Development Simulator",
                "version": "2025.10.1",
                "port": 8123
            },
            "authentication": {
                "enabled": True,
                "token": "dev_simulator_token"
            },
            "entities": [
                {
                    "entity_id": "sensor.living_room_temperature",
                    "domain": "sensor",
                    "device_class": "temperature",
                    "base_value": 22.0,
                    "variance": 2.0,
                    "update_interval": 30,
                    "unit_of_measurement": "°C",
                    "friendly_name": "Living Room Temperature"
                },
                {
                    "entity_id": "sensor.wled_estimated_current",
                    "domain": "sensor",
                    "device_class": "current",
                    "base_value": 0.5,
                    "variance": 0.2,
                    "update_interval": 10,
                    "unit_of_measurement": "A",
                    "friendly_name": "WLED Estimated Current"
                },
                {
                    "entity_id": "sensor.bar_estimated_current",
                    "domain": "sensor",
                    "device_class": "current",
                    "base_value": 0.3,
                    "variance": 0.1,
                    "update_interval": 10,
                    "unit_of_measurement": "A",
                    "friendly_name": "Bar Estimated Current"
                },
                {
                    "entity_id": "sensor.archer_be800_download_speed",
                    "domain": "sensor",
                    "device_class": "data_rate",
                    "base_value": 100.0,
                    "variance": 50.0,
                    "update_interval": 30,
                    "unit_of_measurement": "Mbit/s",
                    "friendly_name": "Archer BE800 Download Speed"
                },
                {
                    "entity_id": "sensor.archer_be800_upload_speed",
                    "domain": "sensor",
                    "device_class": "data_rate",
                    "base_value": 50.0,
                    "variance": 25.0,
                    "update_interval": 30,
                    "unit_of_measurement": "Mbit/s",
                    "friendly_name": "Archer BE800 Upload Speed"
                },
                {
                    "entity_id": "sun.sun",
                    "domain": "sun",
                    "device_class": None,
                    "base_value": "above_horizon",
                    "variance": None,
                    "update_interval": 300,
                    "unit_of_measurement": None,
                    "friendly_name": "Sun"
                },
                {
                    "entity_id": "sensor.slzb_06p7_coordinator_zigbee_chip_temp",
                    "domain": "sensor",
                    "device_class": "temperature",
                    "base_value": 45.0,
                    "variance": 5.0,
                    "update_interval": 60,
                    "unit_of_measurement": "°C",
                    "friendly_name": "SLZB-06P7 Coordinator Zigbee Chip Temperature"
                },
                {
                    "entity_id": "sensor.home_assistant_core_cpu_percent",
                    "domain": "sensor",
                    "device_class": None,
                    "base_value": 15.0,
                    "variance": 10.0,
                    "update_interval": 60,
                    "unit_of_measurement": "%",
                    "friendly_name": "Home Assistant Core CPU Percent"
                }
            ],
            "scenarios": [
                {
                    "name": "normal_operation",
                    "description": "Normal home operation patterns",
                    "event_rate": "medium",
                    "duration": "unlimited"
                },
                {
                    "name": "high_activity",
                    "description": "High activity simulation",
                    "event_rate": "high",
                    "duration": 3600
                },
                {
                    "name": "low_activity",
                    "description": "Low activity simulation",
                    "event_rate": "low",
                    "duration": 3600
                }
            ],
            "logging": {
                "level": "INFO"
            }
        }

    def _apply_environment_overrides(self):
        """Apply environment variable overrides"""
        env_mappings = {
            "SIMULATOR_PORT": ["simulator", "port"],
            "SIMULATOR_AUTH_TOKEN": ["authentication", "token"],
            "SIMULATOR_HA_VERSION": ["simulator", "version"],
            "SIMULATOR_LOG_LEVEL": ["logging", "level"]
        }

        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_config(config_path, value)
                logger.info(f"Override {'.'.join(config_path)} = {value} from {env_var}")

    def _set_nested_config(self, path: list[str], value: Any):
        """Set nested configuration value"""
        config = self.config
        for key in path[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # Convert string values to appropriate types
        if path[-1] == "port":
            value = int(value)
        elif path[-1] == "level":
            value = str(value).upper()

        config[path[-1]] = value

    def _validate_config(self):
        """Validate configuration"""
        required_keys = ["simulator", "authentication", "entities"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required configuration key: {key}")

        # Validate port
        port = self.config["simulator"]["port"]
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise ValueError(f"Invalid port: {port}")

        # Validate entities
        entities = self.config["entities"]
        if not isinstance(entities, list) or len(entities) == 0:
            raise ValueError("Entities must be a non-empty list")

        # Validate each entity
        for entity in entities:
            required_entity_keys = ["entity_id", "domain", "update_interval"]
            for key in required_entity_keys:
                if key not in entity:
                    raise ValueError(f"Entity {entity.get('entity_id', 'unknown')} missing required key: {key}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        config = self.config

        for k in keys:
            if isinstance(config, dict) and k in config:
                config = config[k]
            else:
                return default

        return config

