"""
Configuration Loader for Device Mappings

Loads YAML configuration files for device handlers.
"""

import logging
import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Loads YAML configuration files for device handlers.
    """
    
    def __init__(self, base_path: str | Path | None = None):
        """
        Initialize the configuration loader.
        
        Args:
            base_path: Base path for device mapping configurations.
                      Defaults to `src/device_mappings/` relative to service root.
        """
        if base_path is None:
            # Default to src/device_mappings/ relative to this file
            current_file = Path(__file__).resolve()
            base_path = current_file.parent
        else:
            base_path = Path(base_path)
        
        self.base_path = base_path
        logger.debug(f"Config loader initialized with base path: {base_path}")
    
    def load_config(self, device_type: str) -> dict[str, Any]:
        """
        Load configuration for a device type.
        
        Args:
            device_type: Device type name (e.g., "hue", "wled")
            
        Returns:
            Configuration dictionary, or empty dict if not found
        """
        config_path = self.base_path / device_type / "config.yaml"
        
        if not config_path.exists():
            logger.debug(f"Config file not found: {config_path}")
            return {}
        
        if yaml is None:
            logger.warning("PyYAML not installed, cannot load YAML configs")
            return {}
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                if config is None:
                    return {}
                logger.debug(f"✅ Loaded config for {device_type}: {config_path}")
                return config
        except Exception as e:
            logger.error(f"❌ Error loading config for {device_type}: {e}")
            return {}
    
    def config_exists(self, device_type: str) -> bool:
        """
        Check if configuration file exists for a device type.
        
        Args:
            device_type: Device type name
            
        Returns:
            True if config file exists, False otherwise
        """
        config_path = self.base_path / device_type / "config.yaml"
        return config_path.exists()

