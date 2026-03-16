"""
Prompt Caching (Epic 70, Story 70.8).

Applies cache control markers to system prompt + last 3 turns to reduce
input token costs. Ported from Hermes prompt_caching.py.

Strategy: "system_and_3" — mark system prompt (stable across turns) +
last 3 non-system messages with cache_control headers.

Provider support:
- Anthropic: native cache_control with 5min TTL
- OpenAI: automatic context caching (structure messages for max cache hits)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def apply_cache_control(
    messages: list[dict[str, Any]],
    strategy: str = "system_and_3",
    provider: str = "openai",
) -> list[dict[str, Any]]:
    """Apply cache control markers to messages.

    Args:
        messages: List of message dicts.
        strategy: Caching strategy. "system_and_3" marks system prompt +
                 last 3 messages.
        provider: "openai" or "anthropic".

    Returns:
        Messages with cache markers applied (new list, originals unchanged).
    """
    if not messages:
        return messages

    if strategy != "system_and_3":
        return messages

    if provider == "anthropic":
        return _apply_anthropic_cache(messages)
    return _apply_openai_cache(messages)


def _apply_anthropic_cache(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply Anthropic-style cache_control markers.

    Marks system prompt and last 3 non-system messages with
    cache_control: {"type": "ephemeral"} for 5-minute TTL caching.
    """
    result = []
    for i, msg in enumerate(messages):
        msg_copy = dict(msg)

        # Mark system prompt
        if msg.get("role") == "system" and i == 0:
            msg_copy["cache_control"] = {"type": "ephemeral"}

        result.append(msg_copy)

    # Mark last 3 non-system messages
    non_system_indices = [
        i for i, m in enumerate(result)
        if m.get("role") != "system"
    ]

    for idx in non_system_indices[-3:]:
        result[idx] = dict(result[idx])
        result[idx]["cache_control"] = {"type": "ephemeral"}

    marked_count = sum(1 for m in result if "cache_control" in m)
    logger.debug("Anthropic cache markers applied to %d messages", marked_count)

    return result


def _apply_openai_cache(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Restructure messages for OpenAI automatic context caching.

    OpenAI automatically caches message prefixes. To maximize cache hits:
    1. Keep system prompt as stable prefix (don't change between turns)
    2. Append new messages rather than rebuilding the entire list
    3. Avoid changing message content in the prefix

    This function ensures system prompt is first and stable.
    """
    if not messages:
        return messages

    # Separate system messages from others
    system_msgs = [m for m in messages if m.get("role") == "system"]
    other_msgs = [m for m in messages if m.get("role") != "system"]

    # Stable system prompt first, then conversation
    result = system_msgs + other_msgs

    return result


def estimate_cache_savings(
    messages: list[dict[str, Any]],
    cache_hit_rate: float = 0.75,
) -> dict[str, Any]:
    """Estimate token cost savings from caching.

    Args:
        messages: Message list.
        cache_hit_rate: Estimated cache hit rate (default 75%).

    Returns:
        Dict with savings estimates.
    """
    total_chars = sum(len(m.get("content", "")) for m in messages)
    estimated_tokens = total_chars // 4

    # System prompt tokens (cacheable, stable)
    system_tokens = sum(
        len(m.get("content", "")) // 4
        for m in messages
        if m.get("role") == "system"
    )

    # Cached tokens save ~75% on OpenAI, ~90% on Anthropic
    cached_tokens = int(system_tokens * cache_hit_rate)
    savings_pct = (cached_tokens / estimated_tokens * 100) if estimated_tokens > 0 else 0

    return {
        "total_tokens_estimate": estimated_tokens,
        "cacheable_tokens": system_tokens,
        "expected_cached": cached_tokens,
        "savings_pct": round(savings_pct, 1),
    }
