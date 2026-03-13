"""
Standardized pattern result types for all detectors.

Epic 54, Story 54.3: PatternResult standardization.
All detectors return list[dict] — this module provides a typed structure
that can be used for validation and documentation while maintaining
backward compatibility (PatternResult can be created from raw dicts).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PatternResult:
    """Standardized result from any pattern detector.

    Common fields present in all detector outputs.
    Detector-specific data goes in ``metadata``.
    """

    pattern_type: str
    device_id: str
    confidence: float
    occurrences: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for backward compatibility with existing consumers."""
        result = asdict(self)
        # Flatten top-level for backward compat — consumers expect flat dicts
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PatternResult:
        """Create from a raw detector dict output.

        Extracts common fields and puts the rest in metadata.
        """
        common_fields = {
            "pattern_type",
            "device_id",
            "confidence",
            "occurrences",
            "metadata",
            "created_at",
        }

        pattern_type = data.get("pattern_type", "unknown")
        device_id = data.get("device_id", "")
        confidence = data.get("confidence", 0.0)
        occurrences = data.get("occurrences", 0)
        created_at = data.get("created_at", datetime.utcnow().isoformat())

        # Existing metadata or build from extra fields
        metadata = dict(data.get("metadata", {}))
        for key, value in data.items():
            if key not in common_fields:
                metadata[key] = value

        return cls(
            pattern_type=pattern_type,
            device_id=device_id,
            confidence=confidence,
            occurrences=occurrences,
            metadata=metadata,
            created_at=created_at,
        )

    def __post_init__(self) -> None:
        """Validate confidence is in [0.0, 1.0] range."""
        self.confidence = max(0.0, min(1.0, float(self.confidence)))


# Registry of known pattern types for validation
PATTERN_TYPES = frozenset(
    {
        "time_of_day",
        "co_occurrence",
        "sequence",
        "duration",
        "anomaly",
        "room_based",
        "day_type",
        "frequency",
        "seasonal",
        "contextual",
    }
)


def normalize_results(raw_results: list[dict[str, Any]]) -> list[PatternResult]:
    """Convert raw detector output dicts to PatternResult instances.

    Use this at the aggregation layer (scheduler/API) to normalize
    outputs from all detectors into a consistent format.

    Args:
        raw_results: List of dicts from any detector's detect_patterns()

    Returns:
        List of PatternResult instances
    """
    normalized = []
    for raw in raw_results:
        try:
            normalized.append(PatternResult.from_dict(raw))
        except Exception:
            logger.warning(
                "Failed to normalize pattern result: %s",
                raw.get("pattern_type", "unknown"),
            )
    return normalized
