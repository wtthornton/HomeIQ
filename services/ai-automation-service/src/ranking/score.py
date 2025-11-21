"""
Heuristic Ranking - Transparent, explainable ranking without ML
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RankScore:
    """Ranking score with feature breakdown"""
    total_score: float
    capability_match_ratio: float
    reliability_score: float
    predicted_latency_sec: float
    energy_cost_bucket: int  # 0=low, 1=medium, 2=high
    user_recent_preference: float
    feature_breakdown: dict[str, float]  # Individual feature contributions
    excluded: bool = False
    exclusion_reason: str | None = None


@dataclass
class RankedAutomation:
    """Automation with ranking score"""
    automation: dict[str, Any]
    score: RankScore
    rank: int


def compute_rank_score(
    automation: dict[str, Any],
    capabilities: dict[str, Any],
    reliability_history: dict[str, float] | None = None,
    user_preferences: dict[str, float] | None = None,
) -> RankScore:
    """
    Compute heuristic ranking score for an automation plan.

    Scoring formula:
    +2.0 * capability_match_ratio
    +1.0 * reliability_score (default 0.5 if unknown)
    -0.5 * predicted_latency_sec
    -0.5 * energy_cost_bucket (0/1/2)
    +0.2 * user_recent_preference(device_type)

    Hard filters (exclude if missing mandatory capability):
    - Any candidate missing mandatory capability is excluded

    Args:
        automation: Automation plan (dict or AutomationPlan)
        capabilities: Available capabilities dict
        reliability_history: Optional reliability scores by entity_id
        user_preferences: Optional user preferences by device_type

    Returns:
        RankScore with total score and feature breakdown
    """
    if reliability_history is None:
        reliability_history = {}
    if user_preferences is None:
        user_preferences = {}

    # Extract entities from automation
    entities = _extract_entities(automation)

    # Feature 1: Capability match ratio
    capability_match_ratio = _compute_capability_match(automation, capabilities, entities)

    # Hard filter: Exclude if missing mandatory capabilities
    mandatory_capabilities = _get_mandatory_capabilities(automation)
    missing_mandatory = [cap for cap in mandatory_capabilities if cap not in capabilities]

    if missing_mandatory:
        return RankScore(
            total_score=0.0,
            capability_match_ratio=0.0,
            reliability_score=0.0,
            predicted_latency_sec=0.0,
            energy_cost_bucket=0,
            user_recent_preference=0.0,
            feature_breakdown={},
            excluded=True,
            exclusion_reason=f"Missing mandatory capabilities: {', '.join(missing_mandatory)}",
        )

    # Feature 2: Reliability score
    reliability_score = _compute_reliability_score(entities, reliability_history)

    # Feature 3: Predicted latency
    predicted_latency_sec = _compute_predicted_latency(automation, entities)

    # Feature 4: Energy cost bucket
    energy_cost_bucket = _compute_energy_cost_bucket(automation, entities)

    # Feature 5: User recent preference
    user_recent_preference = _compute_user_preference(automation, entities, user_preferences)

    # Compute weighted score
    feature_breakdown = {
        "capability_match": 2.0 * capability_match_ratio,
        "reliability": 1.0 * reliability_score,
        "latency": -0.5 * predicted_latency_sec,
        "energy_cost": -0.5 * energy_cost_bucket,
        "user_preference": 0.2 * user_recent_preference,
    }

    total_score = sum(feature_breakdown.values())

    return RankScore(
        total_score=total_score,
        capability_match_ratio=capability_match_ratio,
        reliability_score=reliability_score,
        predicted_latency_sec=predicted_latency_sec,
        energy_cost_bucket=energy_cost_bucket,
        user_recent_preference=user_recent_preference,
        feature_breakdown=feature_breakdown,
        excluded=False,
    )


def rank_automations(
    automations: list[dict[str, Any]],
    capabilities: dict[str, Any],
    top_k: int = 10,
    reliability_history: dict[str, float] | None = None,
    user_preferences: dict[str, float] | None = None,
) -> list[RankedAutomation]:
    """
    Rank automations and return top-K.

    Args:
        automations: List of automation plans
        capabilities: Available capabilities dict
        top_k: Number of top results to return
        reliability_history: Optional reliability scores
        user_preferences: Optional user preferences

    Returns:
        List of RankedAutomation sorted by score (highest first)
    """
    # Compute scores
    scored = []
    for automation in automations:
        score = compute_rank_score(
            automation,
            capabilities,
            reliability_history,
            user_preferences,
        )
        scored.append(RankedAutomation(
            automation=automation,
            score=score,
            rank=0,  # Will be set after sorting
        ))

    # Filter out excluded
    included = [s for s in scored if not s.score.excluded]
    [s for s in scored if s.score.excluded]

    # Sort by score (highest first)
    included.sort(key=lambda x: x.score.total_score, reverse=True)

    # Set ranks
    for i, ranked in enumerate(included):
        ranked.rank = i + 1

    # Return top-K
    return included[:top_k]


def _extract_entities(automation: dict[str, Any]) -> list[str]:
    """Extract entity IDs from automation"""
    entities = set()

    # From triggers
    triggers = automation.get("triggers", automation.get("trigger", []))
    if not isinstance(triggers, list):
        triggers = [triggers]
    for trigger in triggers:
        entity_id = trigger.get("entity_id")
        if entity_id:
            if isinstance(entity_id, list):
                entities.update(entity_id)
            else:
                entities.add(entity_id)

    # From actions
    actions = automation.get("actions", automation.get("action", []))
    if not isinstance(actions, list):
        actions = [actions]
    for action in actions:
        entity_id = action.get("entity_id")
        if entity_id:
            if isinstance(entity_id, list):
                entities.update(entity_id)
            else:
                entities.add(entity_id)
        target = action.get("target", {})
        target_entity_id = target.get("entity_id")
        if target_entity_id:
            if isinstance(target_entity_id, list):
                entities.update(target_entity_id)
            else:
                entities.add(target_entity_id)

    return list(entities)


def _compute_capability_match(
    automation: dict[str, Any],
    capabilities: dict[str, Any],
    entities: list[str],
) -> float:
    """Compute capability match ratio (0.0-1.0)"""
    if not entities:
        return 0.0

    required_capabilities = _get_required_capabilities(automation)
    if not required_capabilities:
        return 1.0

    matched = sum(1 for cap in required_capabilities if cap in capabilities)
    return matched / len(required_capabilities) if required_capabilities else 1.0


def _get_mandatory_capabilities(automation: dict[str, Any]) -> list[str]:
    """Get mandatory capabilities required by automation"""
    # Extract from actions
    required = []
    actions = automation.get("actions", automation.get("action", []))
    if not isinstance(actions, list):
        actions = [actions]

    for action in actions:
        service = action.get("service", "")
        # Extract domain.service capabilities
        if "." in service:
            domain = service.split(".")[0]
            required.append(f"{domain}.turn_on")  # Basic capability
            required.append(f"{domain}.turn_off")  # Basic capability

    return required


def _get_required_capabilities(automation: dict[str, Any]) -> list[str]:
    """Get all required capabilities (not just mandatory)"""
    return _get_mandatory_capabilities(automation)


def _compute_reliability_score(
    entities: list[str],
    reliability_history: dict[str, float],
) -> float:
    """Compute reliability score (0.0-1.0)"""
    if not entities:
        return 0.5  # Default

    scores = [reliability_history.get(e, 0.5) for e in entities]
    return sum(scores) / len(scores) if scores else 0.5


def _compute_predicted_latency(
    automation: dict[str, Any],
    entities: list[str],
) -> float:
    """Compute predicted latency in seconds"""
    # Simple heuristic: base latency + per-entity overhead
    base_latency = 0.1  # 100ms base
    per_entity_overhead = 0.05  # 50ms per entity
    return base_latency + (len(entities) * per_entity_overhead)


def _compute_energy_cost_bucket(
    automation: dict[str, Any],
    entities: list[str],
) -> int:
    """Compute energy cost bucket (0=low, 1=medium, 2=high)"""
    # Check for high-power services
    actions = automation.get("actions", automation.get("action", []))
    if not isinstance(actions, list):
        actions = [actions]

    high_power_services = ["climate.set_temperature", "switch.turn_on", "fan.turn_on"]
    has_high_power = any(
        action.get("service") in high_power_services
        for action in actions
    )

    if has_high_power:
        return 2  # High
    if len(entities) > 3:
        return 1  # Medium
    return 0  # Low


def _compute_user_preference(
    automation: dict[str, Any],
    entities: list[str],
    user_preferences: dict[str, float],
) -> float:
    """Compute user preference score (0.0-1.0)"""
    if not entities or not user_preferences:
        return 0.0

    # Extract device types
    device_types = [e.split(".")[0] for e in entities if "." in e]

    # Get preference scores
    scores = [user_preferences.get(dt, 0.0) for dt in device_types]
    return sum(scores) / len(scores) if scores else 0.0

