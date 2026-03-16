"""
Entity Resolution Result DTO.

Represents the result of entity resolution with matched entities and confidence scores.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EntityResolutionResult:
    """Result of entity resolution from user prompt."""

    success: bool
    matched_entities: list[str] = field(default_factory=list)
    matched_areas: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    # Story 62.6: Entities flagged with ai:critical label
    requires_confirmation: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        result: dict[str, Any] = {
            "success": self.success,
            "matched_entities": self.matched_entities,
            "matched_areas": self.matched_areas,
            "confidence_score": self.confidence_score,
            "warnings": self.warnings,
            "requires_confirmation": self.requires_confirmation,
        }
        if self.error:
            result["error"] = self.error
        return result
