"""
Device Mapping Registry

Simple dictionary-based registry for device handlers.
"""

import importlib
import logging
from typing import Any

from .base import DeviceHandler

logger = logging.getLogger(__name__)


class DeviceMappingRegistry:
    """
    Simple dictionary-based registry for device handlers.
    
    Handlers are registered by name and can be looked up by device.
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._handlers: dict[str, DeviceHandler] = {}
        logger.debug("Device mapping registry initialized")
    
    def register(self, name: str, handler: DeviceHandler) -> None:
        """
        Register a device handler.
        
        Args:
            name: Handler name (e.g., "hue", "wled")
            handler: DeviceHandler instance
        """
        if not isinstance(handler, DeviceHandler):
            raise TypeError(f"Handler must be an instance of DeviceHandler, got {type(handler)}")
        
        self._handlers[name] = handler
        logger.info(f"Registered device handler: {name}")
    
    def get_handler(self, name: str) -> DeviceHandler | None:
        """
        Get a handler by name.
        
        Args:
            name: Handler name
            
        Returns:
            DeviceHandler instance or None if not found
        """
        return self._handlers.get(name)
    
    def find_handler(self, device: dict[str, Any]) -> DeviceHandler | None:
        """
        Find a handler that can process the given device.
        
        Args:
            device: Device dictionary from Device Registry
            
        Returns:
            DeviceHandler instance or None if no handler can process the device
        """
        for handler in self._handlers.values():
            if handler.can_handle(device):
                return handler
        return None
    
    def get_handler_name(self, handler: DeviceHandler) -> str | None:
        """
        Get the name of a handler instance.
        
        Args:
            handler: DeviceHandler instance
            
        Returns:
            Handler name or None if not found
        """
        for name, registered_handler in self._handlers.items():
            if registered_handler is handler:
                return name
        return None
    
    def get_all_handlers(self) -> dict[str, DeviceHandler]:
        """
        Get all registered handlers.
        
        Returns:
            Dictionary of handler name -> handler instance
        """
        return self._handlers.copy()
    
    def discover_handlers(self) -> None:
        """
        Auto-discover and register handlers via imports.
        
        This method attempts to import handler modules and register them.
        Handlers should be in subdirectories (e.g., hue/, wled/) and
        should have a `register(registry)` function in their __init__.py.
        """
        # Handler modules to discover
        handler_modules = [
            "device_mappings.hue",
            "device_mappings.wled",
        ]
        
        for module_name in handler_modules:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "register"):
                    module.register(self)
                    logger.debug(f"Discovered handler module: {module_name}")
                else:
                    logger.debug(f"Module {module_name} has no register function, skipping")
            except ImportError as e:
                # Handler module doesn't exist yet (expected for new handlers)
                logger.debug(f"Handler module {module_name} not found (will be created later): {e}")
            except Exception as e:
                logger.warning(f"Error discovering handler module {module_name}: {e}")
    
    def clear(self) -> None:
        """Clear all registered handlers."""
        self._handlers.clear()
        logger.debug("Registry cleared")

