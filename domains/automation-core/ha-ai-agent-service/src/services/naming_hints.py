"""
Naming Convention Hints for Chat (Epic 64, Story 64.6).

Surfaces naming hints when matched entities have low convention scores.
Max 1 hint per turn. Integrates with context_builder.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# Minimum score to not surface hints
_GOOD_SCORE_THRESHOLD = 70

# Labels that require confirmation
_CRITICAL_LABELS = frozenset({"ai:critical", "ai:exclude"})


def build_naming_hints(
    matched_entities: list[dict[str, Any]],
    max_hints: int = 1,
) -> str:
    """Build naming hints for entities with low convention scores.

    Args:
        matched_entities: Entity dicts from entity resolution (must include
            entity_id, friendly_name, area_id, aliases, labels, device_class).
        max_hints: Maximum hints to return (default 1 per turn).

    Returns:
        Hint text for injection into context, or empty string.
    """
    if not matched_entities:
        return ""

    hints: list[str] = []

    for entity in matched_entities:
        if len(hints) >= max_hints:
            break

        entity_id = entity.get("entity_id", "")
        friendly_name = entity.get("friendly_name") or ""
        area_id = entity.get("area_id") or ""
        aliases = entity.get("aliases") or []
        labels = entity.get("labels") or []
        device_class = entity.get("device_class") or ""

        # Check for critical labels
        if isinstance(labels, list):
            critical = _CRITICAL_LABELS.intersection(set(labels))
            if critical:
                hints.append(
                    f"Note: Entity '{friendly_name}' ({entity_id}) has label "
                    f"{', '.join(critical)} — confirm before proceeding."
                )
                continue

        # Quick convention score (simplified — not the full 100-point engine)
        score = _quick_score(entity_id, friendly_name, area_id, aliases, labels, device_class)

        if score < _GOOD_SCORE_THRESHOLD:
            issues = _identify_issues(entity_id, friendly_name, area_id, aliases, labels, device_class)
            if issues:
                hints.append(
                    f"Tip: '{friendly_name}' ({entity_id}) could be improved: "
                    f"{issues[0]}. You can fix this in the HA Setup tab."
                )

    if not hints:
        return ""

    return "\n".join(hints)


def build_not_found_hint(user_query: str) -> str:
    """When entity not found, suggest HA Setup.

    Returns hint text or empty string.
    """
    return (
        "I couldn't find a matching entity. You can review and improve "
        "entity names, aliases, and labels in the HA Setup tab for better recognition."
    )


def _quick_score(
    entity_id: str,
    friendly_name: str,
    area_id: str,
    aliases: list,
    labels: list,
    device_class: str,
) -> int:
    """Quick heuristic score (0-100) for convention compliance."""
    score = 0
    if area_id:
        score += 20
    if isinstance(labels, list) and len(labels) > 0:
        score += 20
    if isinstance(aliases, list) and len(aliases) > 0:
        score += 20
    if friendly_name:
        score += 15
        # Bonus for Title Case
        if friendly_name == friendly_name.title():
            score += 5
    if device_class:
        score += 10
    # Sensor role not checked in quick mode
    score += 10  # baseline
    return min(score, 100)


def _identify_issues(
    entity_id: str,
    friendly_name: str,
    area_id: str,
    aliases: list,
    labels: list,
    device_class: str,
) -> list[str]:
    """Identify the most impactful issues for hint text."""
    issues = []
    if not area_id:
        issues.append("no area assigned")
    if not aliases or (isinstance(aliases, list) and len(aliases) == 0):
        issues.append("no aliases for voice/chat recognition")
    if not labels or (isinstance(labels, list) and len(labels) == 0):
        issues.append("no labels for AI understanding")
    if not device_class:
        issues.append("no device_class set")
    return issues
