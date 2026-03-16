"""
Confidence & Risk Scoring Engine (Epic 68, Story 68.3).

Evaluates each proposed action on two axes:
- Confidence (0-100): historical acceptance, context match, preference alignment
- Risk (low/medium/high/critical): action type and reversibility

Thresholds:
- auto-execute: confidence >= 85, risk = low
- suggest: confidence >= 50 or risk = medium
- suppress: confidence < 30
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Safety-critical entity domains — HARDCODED, never configurable
SAFETY_BLOCKED_DOMAINS = frozenset({"lock", "alarm_control_panel", "camera"})

# Risk classification by entity domain
DOMAIN_RISK_MAP: dict[str, str] = {
    # Low risk — easily reversible
    "light": "low",
    "switch": "low",
    "input_boolean": "low",
    "scene": "low",
    "script": "low",
    "media_player": "low",
    "fan": "low",
    # Medium risk — may cause discomfort
    "climate": "medium",
    "cover": "medium",
    "water_heater": "medium",
    "humidifier": "medium",
    # High risk — user safety
    "lock": "critical",
    "alarm_control_panel": "critical",
    "camera": "critical",
    "siren": "high",
    "valve": "high",
}

# Action reversibility scores (higher = more reversible)
ACTION_REVERSIBILITY: dict[str, float] = {
    "turn_off": 1.0,  # Can always turn back on
    "turn_on": 1.0,   # Can always turn off
    "set_brightness": 0.9,
    "set_temperature": 0.7,  # Takes time to reach new temp
    "set_hvac_mode": 0.7,
    "activate_scene": 0.5,  # Unknown what changed
    "run_script": 0.3,       # Unknown side effects
}


@dataclass
class ActionScore:
    """Result of confidence + risk scoring for a proposed action."""

    confidence: int  # 0-100
    risk_level: str  # low, medium, high, critical
    reversibility: float  # 0.0-1.0
    reasoning: str = ""
    factors: dict[str, float] = field(default_factory=dict)

    @property
    def should_auto_execute(self) -> bool:
        """Whether this action qualifies for autonomous execution."""
        return self.confidence >= 85 and self.risk_level == "low"

    @property
    def should_suggest(self) -> bool:
        """Whether to surface as a suggestion for user approval."""
        return self.confidence >= 50 or self.risk_level == "medium"

    @property
    def should_suppress(self) -> bool:
        """Whether to suppress entirely (too low confidence)."""
        return self.confidence < 30

    @property
    def is_safety_blocked(self) -> bool:
        """Whether the action is blocked by safety guardrails."""
        return self.risk_level == "critical"


class ConfidenceScorer:
    """Scores proposed proactive actions for confidence and risk.

    Uses historical acceptance rates, context match strength,
    and action risk classification.
    """

    def __init__(
        self,
        auto_execute_threshold: int = 85,
        suggest_threshold: int = 50,
        suppress_threshold: int = 30,
    ):
        self.auto_execute_threshold = auto_execute_threshold
        self.suggest_threshold = suggest_threshold
        self.suppress_threshold = suppress_threshold

    def score_action(
        self,
        action_type: str,
        entity_domain: str,
        context_type: str,
        llm_confidence: float,
        acceptance_rate: float | None = None,
        context_match_strength: float = 0.5,
        time_slot: str = "afternoon",
        preference_alignment: float = 0.5,
    ) -> ActionScore:
        """Score a proposed action for confidence and risk.

        Args:
            action_type: e.g. "turn_off", "set_brightness", "set_temperature"
            entity_domain: HA entity domain (light, switch, climate, etc.)
            context_type: what triggered this (weather, energy, historical_pattern, etc.)
            llm_confidence: LLM's self-reported confidence (0.0-1.0)
            acceptance_rate: historical acceptance rate for similar actions (0.0-1.0, None if no history)
            context_match_strength: how well current context matches the action (0.0-1.0)
            time_slot: morning, afternoon, evening, night
            preference_alignment: how well this aligns with known preferences (0.0-1.0)

        Returns:
            ActionScore with confidence, risk, and recommendation.
        """
        # Determine risk level
        risk_level = DOMAIN_RISK_MAP.get(entity_domain, "medium")
        reversibility = ACTION_REVERSIBILITY.get(action_type, 0.5)

        # Safety check — blocked domains are always critical
        if entity_domain in SAFETY_BLOCKED_DOMAINS:
            return ActionScore(
                confidence=0,
                risk_level="critical",
                reversibility=0.0,
                reasoning=f"Safety blocked: {entity_domain} domain cannot be auto-executed",
                factors={"safety_block": 1.0},
            )

        # Calculate confidence from multiple factors
        factors: dict[str, float] = {}

        # Factor 1: LLM confidence (weight: 30%)
        factors["llm_confidence"] = llm_confidence * 0.3

        # Factor 2: Historical acceptance rate (weight: 30%)
        if acceptance_rate is not None:
            factors["acceptance_rate"] = acceptance_rate * 0.3
        else:
            # No history — use neutral baseline
            factors["acceptance_rate"] = 0.5 * 0.3

        # Factor 3: Context match (weight: 20%)
        factors["context_match"] = context_match_strength * 0.2

        # Factor 4: Preference alignment (weight: 10%)
        factors["preference_alignment"] = preference_alignment * 0.1

        # Factor 5: Reversibility bonus (weight: 10%)
        factors["reversibility"] = reversibility * 0.1

        # Sum factors and scale to 0-100
        raw_confidence = sum(factors.values())
        confidence = int(min(100, max(0, raw_confidence * 100)))

        # Build reasoning
        reasoning_parts = []
        if acceptance_rate is not None:
            reasoning_parts.append(
                f"Historical acceptance: {acceptance_rate:.0%}"
            )
        reasoning_parts.append(f"LLM confidence: {llm_confidence:.0%}")
        reasoning_parts.append(f"Context match: {context_match_strength:.0%}")
        reasoning_parts.append(f"Risk: {risk_level} (reversibility: {reversibility:.0%})")

        return ActionScore(
            confidence=confidence,
            risk_level=risk_level,
            reversibility=reversibility,
            reasoning="; ".join(reasoning_parts),
            factors=factors,
        )

    def evaluate_action_route(
        self,
        score: ActionScore,
        autonomous_enabled: bool = True,
        in_quiet_hours: bool = False,
    ) -> str:
        """Determine the action route based on score and configuration.

        Returns:
            "auto_execute", "suggest", or "suppress"
        """
        if score.is_safety_blocked:
            return "suppress"

        if score.should_suppress:
            return "suppress"

        if (
            score.should_auto_execute
            and autonomous_enabled
            and not in_quiet_hours
        ):
            return "auto_execute"

        if score.should_suggest:
            return "suggest"

        return "suppress"
