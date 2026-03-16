"""
Smart Model Routing (Epic 70, Story 70.3).

Routes simple queries to a cheap/fast model and complex queries to the
primary model. Ported from Hermes smart_model_routing.py patterns.

Routing heuristics:
- Cheap model (gpt-4.1-mini): message <160 chars AND <28 words AND
  no code blocks/URLs AND no automation keywords
- Primary model (gpt-5.2-codex): everything else
- Fallback: any routing failure → primary model (never degrade on error)

Relationship to Epic 69: This provides the heuristic base. Epic 69 Story 69.1
adds eval-score-driven adaptive routing on top.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Keywords that indicate complex requests requiring the primary model
AUTOMATION_KEYWORDS = frozenset({
    "create", "set up", "setup", "configure", "automate", "schedule",
    "condition", "trigger", "automation", "blueprint", "scene", "script",
    "routine", "workflow", "if", "when", "whenever", "every",
    "turn on", "turn off", "dim", "brighten", "set temperature",
    "hvac", "thermostat", "notify", "alert",
})

# Patterns that indicate complex requests
COMPLEX_PATTERNS = [
    re.compile(r"```"),           # Code blocks
    re.compile(r"https?://"),     # URLs
    re.compile(r"yaml", re.I),   # YAML references
    re.compile(r"\bapi\b", re.I),  # API references
]


@dataclass
class ModelRoute:
    """Result of model routing decision."""

    model: str
    reason: str
    is_cheap: bool

    @property
    def estimated_cost_factor(self) -> float:
        """Cost factor relative to primary model (1.0 = primary)."""
        return 0.1 if self.is_cheap else 1.0


def choose_model_route(
    message: str,
    primary_model: str = "gpt-5.2-codex",
    cheap_model: str = "gpt-4.1-mini",
    routing_enabled: bool = True,
    max_cheap_chars: int = 160,
    max_cheap_words: int = 28,
) -> ModelRoute:
    """Determine which model to use for a user message.

    Args:
        message: The user's message text.
        primary_model: Model for complex queries.
        cheap_model: Model for simple queries.
        routing_enabled: Master switch for routing.
        max_cheap_chars: Max character count for cheap routing.
        max_cheap_words: Max word count for cheap routing.

    Returns:
        ModelRoute with chosen model and reasoning.
    """
    if not routing_enabled:
        return ModelRoute(
            model=primary_model,
            reason="routing_disabled",
            is_cheap=False,
        )

    try:
        return _evaluate_message(
            message=message,
            primary_model=primary_model,
            cheap_model=cheap_model,
            max_cheap_chars=max_cheap_chars,
            max_cheap_words=max_cheap_words,
        )
    except Exception as e:
        # Fallback: any routing error → primary model
        logger.warning("Model routing error, falling back to primary: %s", e)
        return ModelRoute(
            model=primary_model,
            reason=f"routing_error: {e}",
            is_cheap=False,
        )


def _evaluate_message(
    message: str,
    primary_model: str,
    cheap_model: str,
    max_cheap_chars: int,
    max_cheap_words: int,
) -> ModelRoute:
    """Core routing heuristic evaluation."""
    msg = message.strip()

    # Empty or very short messages → cheap model
    if not msg:
        return ModelRoute(model=cheap_model, reason="empty_message", is_cheap=True)

    # Check length thresholds
    if len(msg) > max_cheap_chars:
        return ModelRoute(
            model=primary_model,
            reason=f"message_length={len(msg)} > {max_cheap_chars}",
            is_cheap=False,
        )

    word_count = len(msg.split())
    if word_count > max_cheap_words:
        return ModelRoute(
            model=primary_model,
            reason=f"word_count={word_count} > {max_cheap_words}",
            is_cheap=False,
        )

    # Check for complex patterns (code blocks, URLs, YAML)
    for pattern in COMPLEX_PATTERNS:
        if pattern.search(msg):
            return ModelRoute(
                model=primary_model,
                reason=f"complex_pattern: {pattern.pattern}",
                is_cheap=False,
            )

    # Check for automation keywords
    msg_lower = msg.lower()
    for keyword in AUTOMATION_KEYWORDS:
        if keyword in msg_lower:
            return ModelRoute(
                model=primary_model,
                reason=f"automation_keyword: {keyword}",
                is_cheap=False,
            )

    # Passes all checks → route to cheap model
    logger.info(
        "Routing to cheap model: len=%d, words=%d, message='%s'",
        len(msg), word_count, msg[:80],
    )
    return ModelRoute(model=cheap_model, reason="simple_query", is_cheap=True)
