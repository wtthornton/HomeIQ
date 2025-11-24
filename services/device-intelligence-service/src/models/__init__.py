# Device Intelligence Service Models Module

# Import all models to ensure they're registered with Base
from .database import (
    Base,
    Device,
    DeviceCapability,
    DeviceEntity,
    DeviceHealthMetric,
    DeviceHygieneIssue,
    DeviceRelationship,
    DiscoverySession,
    CacheStats,
)
from .name_enhancement import NameSuggestion, NamePreference

__all__ = [
    "Base",
    "Device",
    "DeviceCapability",
    "DeviceEntity",
    "DeviceHealthMetric",
    "DeviceHygieneIssue",
    "DeviceRelationship",
    "DiscoverySession",
    "CacheStats",
    "NameSuggestion",
    "NamePreference",
]