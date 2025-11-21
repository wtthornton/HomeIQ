"""
Entity Context Compression Utilities

Compresses entity context to reduce token usage while maintaining essential information.
"""

import logging
from typing import Any

from src.utils.token_counter import count_tokens

logger = logging.getLogger(__name__)


def compress_entity_context(
    entities: dict[str, dict[str, Any]],
    max_tokens: int = 7_000,
    model: str = "gpt-4o",
    relevance_scores: dict[str, float] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Compress entity context by filtering attributes and summarizing capabilities.

    Args:
        entities: Dictionary mapping entity_id to enriched entity data
        max_tokens: Maximum tokens allowed for entity context (default: 7_000)
        model: Model name for token counting
        relevance_scores: Optional dictionary mapping entity_id to relevance score (0.0-1.0).
                         If provided, entities are sorted by relevance before compression.

    Returns:
        Compressed entity dictionary with only essential information
    """
    if not entities:
        return {}

    # NEW: Sort by relevance if scores provided (most relevant first)
    if relevance_scores:
        entities = dict(sorted(
            entities.items(),
            key=lambda x: relevance_scores.get(x[0], 0.0),
            reverse=True,
        ))
        logger.debug(f"📊 Sorted {len(entities)} entities by relevance scores")

    # Essential fields to keep for each entity
    essential_fields = {
        "entity_id",
        "friendly_name",
        "domain",
        "area_id",
        "area_name",
        "state",
        "device_class",
        "unit_of_measurement",
    }

    # Important attributes to keep (filter out verbose ones)
    important_attributes = {
        "friendly_name",
        "device_class",
        "unit_of_measurement",
        "icon",
        "assumed_state",
        "supported_features",
        "current_temperature",
        "temperature",
        "brightness",
        "color_mode",
        "rgb_color",
        "effect",  # Keep effect, but summarize effect_list
    }

    compressed = {}
    total_tokens = 0

    for entity_id, entity_data in entities.items():
        compressed_entity = {}

        # Keep essential fields
        for field in essential_fields:
            if field in entity_data:
                compressed_entity[field] = entity_data[field]

        # Compress attributes - only keep important ones
        attributes = entity_data.get("attributes", {})
        compressed_attributes = {}

        for attr_key in important_attributes:
            if attr_key in attributes:
                compressed_attributes[attr_key] = attributes[attr_key]

        # NEW: Summarize effect_list arrays to reduce token usage
        # Instead of full list like ["rainbow", "theater_chase", "breathe", ...], use summary
        if "effect_list" in attributes:
            effect_list = attributes.get("effect_list", [])
            if isinstance(effect_list, list) and len(effect_list) > 5:
                # Show first 3 effects, then summarize
                effect_summary = ", ".join(effect_list[:3])
                if len(effect_list) > 3:
                    effect_summary += f" (+{len(effect_list) - 3} more effects)"
                compressed_attributes["effect_list_summary"] = effect_summary
                # Don't include full effect_list (saves tokens)
            elif isinstance(effect_list, list):
                # Keep short lists as-is
                compressed_attributes["effect_list"] = effect_list

        # Summarize capabilities instead of listing all
        capabilities = entity_data.get("capabilities", [])
        if capabilities:
            # Extract capability names only (not full details)
            capability_names = []
            for cap in capabilities:
                if isinstance(cap, dict):
                    capability_names.append(cap.get("name", "unknown"))
                elif isinstance(cap, str):
                    capability_names.append(cap)

            # Store as summary string instead of full objects
            compressed_entity["capabilities_summary"] = ", ".join(capability_names[:10])  # Limit to 10
            if len(capability_names) > 10:
                compressed_entity["capabilities_summary"] += f" (+{len(capability_names) - 10} more)"

        # NEW: Remove device intelligence details unless critical (saves ~50-100 tokens per entity)
        # Only keep device_type for capability inference, remove manufacturer/model
        device_intelligence = entity_data.get("device_intelligence", {})
        if device_intelligence:
            # Only keep device_type (needed for capability inference)
            # Remove manufacturer/model (rarely needed, saves tokens)
            device_type = device_intelligence.get("device_type")
            if device_type:
                compressed_entity["device_type"] = device_type
            # Only include full device_intelligence if explicitly marked as critical
            if device_intelligence.get("critical", False):
                compressed_entity["device_intelligence"] = {
                    "manufacturer": device_intelligence.get("manufacturer"),
                    "model": device_intelligence.get("model"),
                    "device_type": device_intelligence.get("device_type"),
                }

        compressed_entity["attributes"] = compressed_attributes
        compressed[entity_id] = compressed_entity

        # Check token count
        entity_str = str(compressed_entity)
        entity_tokens = count_tokens(entity_str, model)
        total_tokens += entity_tokens

        # If we're approaching the limit, stop adding more entities
        if total_tokens > max_tokens * 0.9:
            logger.warning(
                f"Entity context approaching token limit: {total_tokens}/{max_tokens} tokens. "
                f"Stopping compression at {len(compressed)}/{len(entities)} entities.",
            )
            break

    logger.info(
        f"✅ Compressed entity context: {len(compressed)}/{len(entities)} entities, "
        f"~{total_tokens} tokens (limit: {max_tokens})",
    )

    return compressed


def summarize_entity_capabilities(capabilities: list[Any]) -> str:
    """
    Summarize entity capabilities into a compact string.

    Args:
        capabilities: List of capability objects or strings

    Returns:
        Summarized capability string
    """
    if not capabilities:
        return "No capabilities"

    capability_names = []
    for cap in capabilities:
        if isinstance(cap, dict):
            name = cap.get("name", "unknown")
            capability_names.append(name)
        elif isinstance(cap, str):
            capability_names.append(cap)

    if len(capability_names) <= 5:
        return ", ".join(capability_names)
    return ", ".join(capability_names[:5]) + f" (+{len(capability_names) - 5} more)"


def filter_entity_attributes(
    attributes: dict[str, Any],
    keep_important_only: bool = True,
) -> dict[str, Any]:
    """
    Filter entity attributes to keep only important ones.

    Args:
        attributes: Full attributes dictionary
        keep_important_only: If True, only keep important attributes

    Returns:
        Filtered attributes dictionary
    """
    if not keep_important_only:
        return attributes

    important_attributes = {
        "friendly_name",
        "device_class",
        "unit_of_measurement",
        "icon",
        "assumed_state",
        "supported_features",
        "current_temperature",
        "temperature",
        "brightness",
        "color_mode",
        "rgb_color",
        "effect",
        "effect_list",
        "min",
        "max",
        "step",
        "mode",
        "preset_mode",
        "preset_modes",
    }

    filtered = {}
    for key, value in attributes.items():
        if key in important_attributes:
            filtered[key] = value

    return filtered

