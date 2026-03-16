"""
Request Complexity Classifier (Epic 69, Story 69.1).

Rule-based classifier that scores incoming requests on complexity
(low/medium/high) based on: token count, entity count, tool count hint,
conversation depth. Routes: low→cheap, medium→cheap+fallback, high→primary.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ComplexityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ComplexityResult:
    """Result of complexity classification."""

    level: ComplexityLevel
    score: float  # 0.0 (trivial) to 1.0 (very complex)
    factors: dict[str, float] = field(default_factory=dict)
    suggested_model: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "score": round(self.score, 3),
            "factors": self.factors,
            "suggested_model": self.suggested_model,
        }


# Entity-count patterns (rough heuristic)
_ENTITY_PATTERN = re.compile(
    r"\b(?:light|switch|sensor|climate|cover|lock|fan|camera|media_player|vacuum|automation|script|scene)"
    r"\.\w+",
    re.IGNORECASE,
)

# Tool-hint keywords
_MULTI_TOOL_KEYWORDS = frozenset({
    "and then", "after that", "also", "as well", "plus",
    "create and", "set up and", "first", "second", "finally",
    "multiple", "all", "every room", "each",
})


class ComplexityClassifier:
    """Classifies request complexity for model routing decisions."""

    def __init__(
        self,
        token_high_threshold: int = 200,
        token_medium_threshold: int = 80,
        entity_high_threshold: int = 3,
        depth_high_threshold: int = 8,
    ):
        self.token_high = token_high_threshold
        self.token_medium = token_medium_threshold
        self.entity_high = entity_high_threshold
        self.depth_high = depth_high_threshold

    def classify(
        self,
        message: str,
        conversation_depth: int = 0,
        entity_ids: list[str] | None = None,
        previous_tool_calls: int = 0,
    ) -> ComplexityResult:
        """Classify request complexity.

        Args:
            message: User message text.
            conversation_depth: Number of previous turns in conversation.
            entity_ids: Resolved entity IDs from the message (if available).
            previous_tool_calls: Number of tool calls in this conversation so far.

        Returns:
            ComplexityResult with level, score, and contributing factors.
        """
        factors: dict[str, float] = {}

        # Factor 1: Token/character count (0.0-1.0)
        char_count = len(message.strip())
        word_count = len(message.split())
        if char_count > self.token_high:
            factors["token_count"] = 1.0
        elif char_count > self.token_medium:
            factors["token_count"] = 0.5
        else:
            factors["token_count"] = 0.1

        # Factor 2: Entity count (0.0-1.0)
        if entity_ids:
            entity_count = len(entity_ids)
        else:
            entity_count = len(_ENTITY_PATTERN.findall(message))
        if entity_count >= self.entity_high:
            factors["entity_count"] = 1.0
        elif entity_count >= 1:
            factors["entity_count"] = 0.4
        else:
            factors["entity_count"] = 0.0

        # Factor 3: Tool count hint (0.0-1.0)
        msg_lower = message.lower()
        multi_tool_hits = sum(1 for kw in _MULTI_TOOL_KEYWORDS if kw in msg_lower)
        if multi_tool_hits >= 2:
            factors["tool_hint"] = 0.8
        elif multi_tool_hits >= 1:
            factors["tool_hint"] = 0.4
        else:
            factors["tool_hint"] = 0.0

        # Factor 4: Conversation depth (0.0-1.0)
        if conversation_depth >= self.depth_high:
            factors["conversation_depth"] = 0.8
        elif conversation_depth >= 4:
            factors["conversation_depth"] = 0.4
        elif conversation_depth >= 1:
            factors["conversation_depth"] = 0.2
        else:
            factors["conversation_depth"] = 0.0

        # Factor 5: Previous tool usage (0.0-1.0)
        if previous_tool_calls >= 5:
            factors["prior_tools"] = 0.7
        elif previous_tool_calls >= 2:
            factors["prior_tools"] = 0.3
        else:
            factors["prior_tools"] = 0.0

        # Weighted score
        weights = {
            "token_count": 0.25,
            "entity_count": 0.25,
            "tool_hint": 0.20,
            "conversation_depth": 0.15,
            "prior_tools": 0.15,
        }
        score = sum(factors.get(k, 0.0) * w for k, w in weights.items())

        # Classify
        if score >= 0.55:
            level = ComplexityLevel.HIGH
        elif score >= 0.30:
            level = ComplexityLevel.MEDIUM
        else:
            level = ComplexityLevel.LOW

        return ComplexityResult(
            level=level,
            score=score,
            factors=factors,
        )
