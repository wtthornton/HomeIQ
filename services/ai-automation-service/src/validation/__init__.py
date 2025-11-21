"""
Validation package for automation suggestions.

Provides device and entity validation to ensure automation suggestions
only reference devices that actually exist in the Home Assistant system.
"""

from .device_validator import DeviceValidator, ValidationResult

__all__ = ["DeviceValidator", "ValidationResult"]
