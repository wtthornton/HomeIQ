"""
Device Mapping Library - Plugin Registry

This module provides a plugin-based architecture for device-specific mappings.
Handlers are registered via imports in this file.
"""

from .registry import DeviceMappingRegistry

# Create global registry instance
_registry: DeviceMappingRegistry | None = None


def get_registry() -> DeviceMappingRegistry:
    """Get or create the global device mapping registry."""
    global _registry
    if _registry is None:
        _registry = DeviceMappingRegistry()
        # Auto-discover and register handlers
        _registry.discover_handlers()
    return _registry


def reload_registry() -> DeviceMappingRegistry:
    """Reload the registry (clears cache and re-discovers handlers)."""
    global _registry
    _registry = DeviceMappingRegistry()
    _registry.discover_handlers()
    return _registry


__all__ = ["DeviceMappingRegistry", "get_registry", "reload_registry"]

