"""
Configuration Manager - Simple .env file reader/writer
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

SENSITIVE_KEY_PATTERNS = ("TOKEN", "API_KEY", "SECRET", "PASSWORD", "PRIVATE_KEY", "ACCESS_KEY")
MASK_VALUE = "********"

class ConfigManager:
    """Simple configuration manager for .env files"""

    def __init__(self, config_dir: str = "infrastructure"):
        """
        Initialize config manager
        
        Args:
            config_dir: Directory containing .env files
        """
        self.config_dir = Path(config_dir)
        self.allow_secret_writes = os.getenv('ADMIN_API_ALLOW_SECRET_WRITES', 'false').lower() == 'true'
        if not self.config_dir.exists():
            logger.warning(f"Config directory {config_dir} does not exist")

    def list_services(self) -> list[str]:
        """
        List all available service configurations
        
        Returns:
            List of service names
        """
        services = []
        if not self.config_dir.exists():
            return services

        for file in self.config_dir.glob(".env.*"):
            # Skip .env.example and template files
            if file.name.endswith(".example") or file.name.endswith(".template"):
                continue
            # Extract service name from .env.{service}
            if file.name.startswith(".env."):
                service_name = file.name.replace(".env.", "")
                services.append(service_name)

        return sorted(services)

    def read_config(self, service: str) -> dict[str, str]:
        """
        Read configuration for a service
        
        Args:
            service: Service name (e.g., 'websocket', 'weather')
            
        Returns:
            Dictionary of configuration key-value pairs
            
        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        env_file = self.config_dir / f".env.{service}"

        if not env_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {env_file}")

        config = {}
        with open(env_file) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Parse key=value
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
                else:
                    logger.warning(
                        f"Invalid line {line_num} in {env_file}: {line}"
                    )

        logger.info(f"Read {len(config)} settings for {service}")
        return config

    def write_config(
        self,
        service: str,
        updates: dict[str, str],
        create_if_missing: bool = False
    ) -> dict[str, str]:
        """
        Update configuration for a service
        
        Args:
            service: Service name
            updates: Dictionary of key-value pairs to update
            create_if_missing: Create file if it doesn't exist
            
        Returns:
            Updated configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist and create_if_missing=False
        """
        env_file = self.config_dir / f".env.{service}"

        if not env_file.exists() and not create_if_missing:
            raise FileNotFoundError(f"Configuration file not found: {env_file}")

        if not self.allow_secret_writes:
            blocked = [key for key in updates if self._is_sensitive_key(key)]
            if blocked:
                raise PermissionError(
                    f"Updating sensitive keys via API is disabled: {', '.join(blocked)}"
                )

        # Read existing config if file exists
        lines = []
        if env_file.exists():
            with open(env_file) as f:
                lines = f.readlines()

        # Update or add new values
        updated_keys = set()
        new_lines = []

        for line in lines:
            stripped = line.strip()

            # Keep comments and empty lines as-is
            if not stripped or stripped.startswith('#'):
                new_lines.append(line)
                continue

            # Update existing key
            if '=' in stripped:
                key = stripped.split('=')[0].strip()
                if key in updates:
                    new_lines.append(f"{key}={updates[key]}\n")
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        # Add new keys that weren't in the file
        for key, value in updates.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}\n")
                updated_keys.add(key)

        # Write back
        with open(env_file, 'w') as f:
            f.writelines(new_lines)

        # Set secure permissions (owner read/write only) - ignore errors for mounted volumes
        try:
            os.chmod(env_file, 0o600)
        except PermissionError:
            # Ignore permission errors for mounted volumes (like Docker bind mounts)
            logger.debug(f"Could not change permissions for {env_file} (mounted volume)")
        except Exception as e:
            logger.warning(f"Could not change permissions for {env_file}: {e}")

        logger.info(
            f"Updated {len(updated_keys)} settings for {service}"
        )

        # Return updated config
        return self.read_config(service)

    def validate_config(self, service: str, config: dict[str, str]) -> dict[str, list[str]]:
        """
        Validate service configuration against service-specific rules and requirements.
        
        Performs comprehensive validation including URL format checking, required field
        verification, numeric range validation, and service-specific business rules.
        Returns detailed validation results with categorized errors and warnings.
        
        Complexity: C (19) - High complexity due to service-specific validation rules
        
        Args:
            service (str): Service identifier (e.g., 'websocket', 'weather', 'influxdb')
            config (Dict[str, str]): Configuration dictionary with key-value pairs
            
        Returns:
            Dict[str, List[str]]: Validation result containing:
                - 'errors' (List[str]): Blocking validation errors that prevent service start
                - 'warnings' (List[str]): Non-blocking issues that should be addressed
                - 'valid' (bool): True if no errors found
        
        Service-Specific Validation Rules:
            - websocket: Validates HA_URL (ws://), HA_TOKEN (min length 10)
            - weather: Validates API key, latitude (-90 to 90), longitude (-180 to 180)
            - influxdb: Validates URL (http://), token, org, bucket presence
        
        Example:
            >>> manager = ConfigManager()
            >>> result = manager.validate_config("websocket", {
            ...     "HA_URL": "ws://192.168.1.86:8123",
            ...     "HA_TOKEN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            ... })
            >>> if result['valid']:
            ...     print("Configuration is valid")
            >>> else:
            ...     print(f"Errors: {result['errors']}")
        
        Note:
            High complexity arises from:
            - Multiple service types with different validation rules
            - Nested validation logic for each service
            - Type checking and range validation
            - URL format validation
            - Business rule enforcement
        """
        errors = []
        warnings = []

        # Service-specific validation
        if service == "websocket":
            if "HA_URL" not in config:
                errors.append("HA_URL is required")
            elif not config["HA_URL"].startswith("ws://") and not config["HA_URL"].startswith("wss://"):
                errors.append("HA_URL must start with ws:// or wss://")

            if "HA_TOKEN" not in config:
                errors.append("HA_TOKEN is required")
            elif len(config.get("HA_TOKEN", "")) < 10:
                warnings.append("HA_TOKEN seems too short")

        elif service == "weather":
            if "WEATHER_API_KEY" not in config:
                errors.append("WEATHER_API_KEY is required")

            try:
                lat = float(config.get("WEATHER_LAT", "0"))
                if not -90 <= lat <= 90:
                    errors.append("WEATHER_LAT must be between -90 and 90")
            except ValueError:
                errors.append("WEATHER_LAT must be a number")

            try:
                lon = float(config.get("WEATHER_LON", "0"))
                if not -180 <= lon <= 180:
                    errors.append("WEATHER_LON must be between -180 and 180")
            except ValueError:
                errors.append("WEATHER_LON must be a number")

        elif service == "influxdb":
            if "INFLUXDB_URL" not in config:
                errors.append("INFLUXDB_URL is required")
            elif not config["INFLUXDB_URL"].startswith("http"):
                errors.append("INFLUXDB_URL must start with http:// or https://")

            if "INFLUXDB_TOKEN" not in config:
                errors.append("INFLUXDB_TOKEN is required")

            if "INFLUXDB_ORG" not in config:
                errors.append("INFLUXDB_ORG is required")

            if "INFLUXDB_BUCKET" not in config:
                errors.append("INFLUXDB_BUCKET is required")

        return {
            "errors": errors,
            "warnings": warnings,
            "valid": len(errors) == 0
        }

    def get_config_template(self, service: str) -> dict[str, dict[str, str]]:
        """
        Get configuration template with field metadata
        
        Args:
            service: Service name
            
        Returns:
            Dictionary with field definitions
        """
        templates = {
            "websocket": {
                "HA_URL": {
                    "type": "url",
                    "required": True,
                    "sensitive": False,
                    "description": "Home Assistant WebSocket URL",
                    "placeholder": "ws://192.168.1.100:8123/api/websocket",
                    "default": ""
                },
                "HA_TOKEN": {
                    "type": "password",
                    "required": True,
                    "sensitive": True,
                    "description": "Home Assistant Long-Lived Access Token",
                    "placeholder": "Your HA access token",
                    "default": ""
                },
                "HA_SSL_VERIFY": {
                    "type": "boolean",
                    "required": False,
                    "sensitive": False,
                    "description": "Verify SSL certificates",
                    "default": "true"
                },
                "HA_RECONNECT_DELAY": {
                    "type": "number",
                    "required": False,
                    "sensitive": False,
                    "description": "Reconnect delay in seconds",
                    "default": "5"
                }
            },
            "weather": {
                "WEATHER_API_KEY": {
                    "type": "password",
                    "required": True,
                    "sensitive": True,
                    "description": "OpenWeatherMap API Key",
                    "placeholder": "Your OpenWeatherMap API key",
                    "default": ""
                },
                "WEATHER_LAT": {
                    "type": "number",
                    "required": True,
                    "sensitive": False,
                    "description": "Latitude",
                    "placeholder": "51.5074",
                    "default": "51.5074"
                },
                "WEATHER_LON": {
                    "type": "number",
                    "required": True,
                    "sensitive": False,
                    "description": "Longitude",
                    "placeholder": "-0.1278",
                    "default": "-0.1278"
                },
                "WEATHER_UNITS": {
                    "type": "select",
                    "required": False,
                    "sensitive": False,
                    "description": "Temperature units",
                    "options": ["metric", "imperial"],
                    "default": "metric"
                },
                "WEATHER_CACHE_SECONDS": {
                    "type": "number",
                    "required": False,
                    "sensitive": False,
                    "description": "Cache duration in seconds",
                    "default": "300"
                }
            },
            "influxdb": {
                "INFLUXDB_URL": {
                    "type": "url",
                    "required": True,
                    "sensitive": False,
                    "description": "InfluxDB URL",
                    "placeholder": "http://influxdb:8086",
                    "default": "http://influxdb:8086"
                },
                "INFLUXDB_TOKEN": {
                    "type": "password",
                    "required": True,
                    "sensitive": True,
                    "description": "InfluxDB Access Token",
                    "placeholder": "Your InfluxDB token",
                    "default": ""
                },
                "INFLUXDB_ORG": {
                    "type": "text",
                    "required": True,
                    "sensitive": False,
                    "description": "InfluxDB Organization",
                    "default": "home-assistant"
                },
                "INFLUXDB_BUCKET": {
                    "type": "text",
                    "required": True,
                    "sensitive": False,
                    "description": "InfluxDB Bucket",
                    "default": "ha_events"
                }
            }
        }

        return templates.get(service, {})

    def sanitize_config(self, config: dict[str, str]) -> dict[str, str]:
        """Return a copy of the provided config with sensitive values masked."""
        sanitized: dict[str, str] = {}
        for key, value in config.items():
            if self._is_sensitive_key(key) and value:
                sanitized[key] = MASK_VALUE
            else:
                sanitized[key] = value
        return sanitized

    def _is_sensitive_key(self, key: str) -> bool:
        upper_key = key.upper()
        return any(pattern in upper_key for pattern in SENSITIVE_KEY_PATTERNS)


# Global instance
config_manager = ConfigManager()

