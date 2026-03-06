"""
Memory integration for rating feedback.

Story 30.3: Saves memories when users rate automations to capture
positive/negative outcomes for the Memory Brain system.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeiq_memory import MemoryClient

logger = logging.getLogger(__name__)


async def save_rating_memory(
    memory_client: "MemoryClient",
    automation_id: str,
    rule_pattern: str,
    rating: int,
    comment: str | None = None,
    entity_ids: list[str] | None = None,
) -> int | None:
    """Save memory based on user rating.

    Only saves memories for strong signals (rating <= 2 or >= 4).
    Neutral ratings (3) are skipped to avoid noise.

    Args:
        memory_client: Initialized MemoryClient instance.
        automation_id: ID of the automation being rated.
        rule_pattern: The rule pattern (e.g., 'binary_sensor_to_light').
        rating: User rating from 1-5.
        comment: Optional user comment explaining the rating.
        entity_ids: Optional list of related Home Assistant entity IDs.

    Returns:
        The memory ID if saved, None if skipped or failed.
    """
    from homeiq_memory import MemoryType, SourceChannel

    if not memory_client.available:
        logger.warning("Memory client not available, skipping rating memory")
        return None

    if rating <= 2:
        content = f"Automation '{automation_id}' ({rule_pattern}) underperformed"
        if comment:
            content += f" - user feedback: {comment}"
        tags = ["automation-outcome", "negative", rule_pattern]
    elif rating >= 4:
        content = f"Automation '{automation_id}' ({rule_pattern}) well-received by user"
        if comment:
            content += f" - user feedback: {comment}"
        tags = ["automation-outcome", "positive", rule_pattern]
    else:
        logger.debug("Neutral rating (%d), skipping memory save", rating)
        return None

    try:
        memory = await memory_client.save(
            content=content,
            memory_type=MemoryType.OUTCOME,
            source_channel=SourceChannel.EXPLICIT,
            source_service="rule-recommendation-ml",
            entity_ids=entity_ids,
            tags=tags,
            metadata={
                "automation_id": automation_id,
                "rule_pattern": rule_pattern,
                "rating": rating,
                "rating_category": "negative" if rating <= 2 else "positive",
            },
            confidence=0.8 if rating in (1, 5) else 0.6,
        )
        logger.info(
            "Saved rating memory id=%d for automation=%s rating=%d",
            memory.id,
            automation_id,
            rating,
        )
        return memory.id
    except Exception:
        logger.exception("Failed to save rating memory for automation=%s", automation_id)
        return None
