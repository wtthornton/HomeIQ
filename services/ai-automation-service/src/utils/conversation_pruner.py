"""
Conversation History Pruning Utilities

Prunes conversation history to keep only recent turns and reduce token usage.
"""

import logging
from typing import Any

from src.utils.token_counter import count_tokens

logger = logging.getLogger(__name__)


def prune_conversation_history(
    history: list[dict[str, Any]],
    max_turns: int = 3,
    max_tokens: int = 1_000,
    model: str = "gpt-4o",
) -> list[dict[str, Any]]:
    """
    Prune conversation history to keep only recent turns.

    Args:
        history: List of conversation turn dictionaries
        max_turns: Maximum number of recent turns to keep
        max_tokens: Maximum tokens allowed for history
        model: Model name for token counting

    Returns:
        Pruned conversation history
    """
    if not history:
        return []

    # Keep only last N turns
    if len(history) <= max_turns:
        pruned = history
    else:
        pruned = history[-max_turns:]
        logger.info(
            f"Pruned conversation history: {len(history)} → {len(pruned)} turns "
            f"(keeping last {max_turns} turns)",
        )

    # Check token count and truncate if needed
    history_text = _history_to_text(pruned)
    history_tokens = count_tokens(history_text, model)

    if history_tokens > max_tokens:
        logger.warning(
            f"Conversation history exceeds token limit: {history_tokens} > {max_tokens}. "
            f"Truncating older turns.",
        )
        # Remove oldest turns until under limit
        while history_tokens > max_tokens and len(pruned) > 1:
            pruned = pruned[1:]  # Remove oldest turn
            history_text = _history_to_text(pruned)
            history_tokens = count_tokens(history_text, model)

        logger.info(
            f"Truncated conversation history to {len(pruned)} turns "
            f"({history_tokens} tokens, limit: {max_tokens})",
        )

    return pruned


def _history_to_text(history: list[dict[str, Any]]) -> str:
    """
    Convert conversation history to text for token counting.

    Args:
        history: List of conversation turn dictionaries

    Returns:
        Text representation of history
    """
    text_parts = []
    for turn in history:
        role = turn.get("role", "user")
        content = turn.get("content", "") or turn.get("message", "")
        if content:
            text_parts.append(f"{role}: {content}")

    return "\n".join(text_parts)


def summarize_old_context(
    old_turns: list[dict[str, Any]],
    model: str = "gpt-4o",
) -> str:
    """
    Summarize older conversation context (future enhancement).

    For now, returns a simple summary. In the future, could use LLM to summarize.

    Args:
        old_turns: List of older conversation turns
        model: Model name (for future LLM summarization)

    Returns:
        Summary string of old context
    """
    if not old_turns:
        return ""

    # Simple summary: count turns and extract key topics
    user_messages = [
        turn.get("content", "") or turn.get("message", "")
        for turn in old_turns
        if turn.get("role") == "user"
    ]

    if len(user_messages) == 1:
        return f"Previous query: {user_messages[0][:100]}..."
    if len(user_messages) > 1:
        return f"{len(user_messages)} previous queries about: {', '.join([m[:50] for m in user_messages[:3]])}..."

    return f"{len(old_turns)} previous conversation turns"

