"""
Adaptive Model Router (Epic 69, Story 69.2).

Selects the model per-request based on complexity classification and
recent eval scores. If eval scores for a request category drop below
threshold, auto-upgrade that category to the primary model.

Builds on Epic 70's static smart routing with eval-score feedback.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .complexity_classifier import ComplexityClassifier, ComplexityLevel, ComplexityResult

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """A recorded routing decision for correlation analysis."""

    timestamp: float
    conversation_id: str
    complexity: ComplexityResult
    chosen_model: str
    reason: str
    overridden: bool = False
    override_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "conversation_id": self.conversation_id,
            "complexity_level": self.complexity.level.value,
            "complexity_score": round(self.complexity.score, 3),
            "chosen_model": self.chosen_model,
            "reason": self.reason,
            "overridden": self.overridden,
            "override_reason": self.override_reason,
        }


@dataclass
class RoutingConfig:
    """Per-category routing configuration."""

    primary_model: str = "gpt-5.2-codex"
    cheap_model: str = "gpt-4.1-mini"
    eval_floor: float = 70.0  # Min eval score before auto-upgrade
    routing_enabled: bool = True
    locked_model: str | None = None  # Lock to specific model (incident override)


@dataclass
class CategoryEvalScores:
    """Recent eval scores for a complexity category."""

    category: ComplexityLevel
    recent_scores: list[float] = field(default_factory=list)
    rolling_avg: float = 0.0
    sample_count: int = 0

    @property
    def below_floor(self) -> bool:
        return self.rolling_avg > 0 and self.rolling_avg < 70.0


class ModelRouter:
    """Adaptive model router with eval-score feedback loop."""

    def __init__(
        self,
        config: RoutingConfig | None = None,
        classifier: ComplexityClassifier | None = None,
    ):
        self.config = config or RoutingConfig()
        self.classifier = classifier or ComplexityClassifier()

        # Eval score tracking per category
        self._category_scores: dict[ComplexityLevel, CategoryEvalScores] = {
            level: CategoryEvalScores(category=level)
            for level in ComplexityLevel
        }

        # Recent routing decisions (ring buffer, max 1000)
        self._decisions: list[RoutingDecision] = []
        self._max_decisions = 1000

        # Per-agent model overrides (from admin config)
        self._agent_overrides: dict[str, str] = {}

    def route(
        self,
        message: str,
        conversation_id: str = "",
        conversation_depth: int = 0,
        entity_ids: list[str] | None = None,
        previous_tool_calls: int = 0,
        agent_id: str | None = None,
    ) -> RoutingDecision:
        """Route a request to the appropriate model.

        Args:
            message: User message.
            conversation_id: For tracking/correlation.
            conversation_depth: Number of previous turns.
            entity_ids: Resolved entities.
            previous_tool_calls: Prior tool calls in conversation.
            agent_id: Agent identifier for per-agent overrides.

        Returns:
            RoutingDecision with chosen model.
        """
        # Check model lock (incident mode)
        if self.config.locked_model:
            decision = RoutingDecision(
                timestamp=time.time(),
                conversation_id=conversation_id,
                complexity=ComplexityResult(
                    level=ComplexityLevel.HIGH, score=1.0,
                ),
                chosen_model=self.config.locked_model,
                reason="model_locked",
                overridden=True,
                override_reason=f"Locked to {self.config.locked_model}",
            )
            self._record_decision(decision)
            return decision

        # Check per-agent override
        if agent_id and agent_id in self._agent_overrides:
            override_model = self._agent_overrides[agent_id]
            complexity = self.classifier.classify(
                message, conversation_depth, entity_ids, previous_tool_calls,
            )
            decision = RoutingDecision(
                timestamp=time.time(),
                conversation_id=conversation_id,
                complexity=complexity,
                chosen_model=override_model,
                reason="agent_override",
                overridden=True,
                override_reason=f"Agent {agent_id} override to {override_model}",
            )
            self._record_decision(decision)
            return decision

        if not self.config.routing_enabled:
            decision = RoutingDecision(
                timestamp=time.time(),
                conversation_id=conversation_id,
                complexity=ComplexityResult(
                    level=ComplexityLevel.HIGH, score=1.0,
                ),
                chosen_model=self.config.primary_model,
                reason="routing_disabled",
            )
            self._record_decision(decision)
            return decision

        # Classify complexity
        complexity = self.classifier.classify(
            message, conversation_depth, entity_ids, previous_tool_calls,
        )

        # Select model based on complexity + eval scores
        chosen_model, reason, overridden, override_reason = self._select_model(complexity)

        decision = RoutingDecision(
            timestamp=time.time(),
            conversation_id=conversation_id,
            complexity=complexity,
            chosen_model=chosen_model,
            reason=reason,
            overridden=overridden,
            override_reason=override_reason,
        )
        self._record_decision(decision)
        return decision

    def record_eval_score(
        self,
        complexity_level: ComplexityLevel,
        score: float,
        max_history: int = 50,
    ) -> None:
        """Record an eval score for a complexity category.

        This feeds the adaptive routing feedback loop.
        """
        cat_scores = self._category_scores[complexity_level]
        cat_scores.recent_scores.append(score)
        if len(cat_scores.recent_scores) > max_history:
            cat_scores.recent_scores = cat_scores.recent_scores[-max_history:]
        cat_scores.sample_count = len(cat_scores.recent_scores)
        cat_scores.rolling_avg = (
            sum(cat_scores.recent_scores) / len(cat_scores.recent_scores)
            if cat_scores.recent_scores else 0.0
        )

    def set_agent_override(self, agent_id: str, model: str | None) -> None:
        """Set or clear a per-agent model override."""
        if model is None:
            self._agent_overrides.pop(agent_id, None)
        else:
            self._agent_overrides[agent_id] = model

    def get_routing_table(self) -> dict[str, Any]:
        """Get current routing table for GET /api/model-routing."""
        return {
            "config": {
                "primary_model": self.config.primary_model,
                "cheap_model": self.config.cheap_model,
                "eval_floor": self.config.eval_floor,
                "routing_enabled": self.config.routing_enabled,
                "locked_model": self.config.locked_model,
            },
            "category_scores": {
                level.value: {
                    "rolling_avg": round(scores.rolling_avg, 1),
                    "sample_count": scores.sample_count,
                    "below_floor": scores.below_floor,
                }
                for level, scores in self._category_scores.items()
            },
            "agent_overrides": dict(self._agent_overrides),
            "recent_decisions_count": len(self._decisions),
        }

    def get_recent_decisions(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent routing decisions for correlation analysis."""
        return [d.to_dict() for d in self._decisions[-limit:]]

    def _select_model(
        self,
        complexity: ComplexityResult,
    ) -> tuple[str, str, bool, str]:
        """Select model based on complexity and eval scores.

        Returns: (model, reason, overridden, override_reason)
        """
        # High complexity → always primary
        if complexity.level == ComplexityLevel.HIGH:
            return self.config.primary_model, "high_complexity", False, ""

        # Check eval scores for this category
        cat_scores = self._category_scores[complexity.level]

        # If cheap model eval scores dropped below floor, auto-upgrade
        if cat_scores.below_floor and cat_scores.sample_count >= 5:
            return (
                self.config.primary_model,
                f"eval_auto_upgrade_{complexity.level.value}",
                True,
                f"Eval avg {cat_scores.rolling_avg:.1f} < floor {self.config.eval_floor}",
            )

        # Low complexity → cheap model
        if complexity.level == ComplexityLevel.LOW:
            return self.config.cheap_model, "low_complexity", False, ""

        # Medium → cheap with fallback awareness
        return self.config.cheap_model, "medium_complexity_cheap", False, ""

    def _record_decision(self, decision: RoutingDecision) -> None:
        """Record a routing decision in the ring buffer."""
        self._decisions.append(decision)
        if len(self._decisions) > self._max_decisions:
            self._decisions = self._decisions[-self._max_decisions:]
