# Device Intelligence Service Models Module

# Import all models to ensure they're registered with Base
from .database import (
    Base,
    CacheStats,
    Device,
    DeviceCapability,
    DeviceEntity,
    DeviceHealthMetric,
    DeviceHygieneIssue,
    DeviceRelationship,
    DiscoverySession,
)
from .device_knowledge import (
    ClaimType,
    DeviceKnowledgeClaim,
    EvidenceClass,
    SubjectKind,
)
from .name_enhancement import NamePreference, NameSuggestion

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
    "DeviceKnowledgeClaim",
    "SubjectKind",
    "EvidenceClass",
    "ClaimType",
]
