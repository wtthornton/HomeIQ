"""
Shared confidence calculation utility.

Epic 39: Query Service
Extracted to avoid duplicate confidence logic across processor and clarification service.
"""

from typing import Any


def calculate_entity_confidence(
    entities: list[dict[str, Any]],
    base: float = 0.5,
    entity_weight: float = 0.08,
    quality_weight: float = 0.15,
    cap: float = 0.95,
) -> float:
    """Calculate confidence score from extracted entities.

    Args:
        entities: List of entity dicts (must have optional 'entity_id' and 'confidence' keys).
        base: Starting confidence when no entities are present.
        entity_weight: Additive boost per entity.
        quality_weight: Additive boost scaled by average entity quality.
        cap: Maximum confidence value.

    Returns:
        Confidence score clamped to [0, cap].
    """
    if not entities:
        return base

    entity_count = len(entities)
    quality_score = sum(
        (1.0 if e.get("entity_id") else 0.5) * e.get("confidence", 0.7)
        for e in entities
    ) / entity_count

    return min(cap, base + (entity_count * entity_weight) + (quality_score * quality_weight))
