"""
Context Compression (Epic 70, Story 70.4).

When conversation exceeds 50% of context window, preserve first 3 + last 4
turns, LLM-summarize everything in between. Replaces hard truncation in
prompt_assembly_service.py.

Algorithm:
1. Check token count after each iteration
2. If tokens > context_length × threshold → trigger compression
3. Protect first N turns (system prompt + initial exchange) and last M turns
4. Summarize middle turns via cheap model with temperature=0.3
5. Sanitize orphaned tool_call/tool_result pairs
6. If summarization fails → drop middle turns (graceful fallback)
"""

from __future__ import annotations

import logging
from typing import Any

from ..utils.token_counter import count_message_tokens

logger = logging.getLogger(__name__)

COMPRESSION_PROMPT = """Summarize the following conversation segment concisely.
Capture: actions taken, results obtained, decisions made, and any data needed to continue.
Keep under 600 words. Output only the summary, no preamble.

Conversation segment:
{segment}"""


class ContextCompressor:
    """Intelligently compresses conversation context to extend usable window."""

    def __init__(
        self,
        threshold_pct: float = 0.5,
        protect_head: int = 3,
        protect_tail: int = 4,
        max_context_tokens: int = 16_000,
    ):
        self.threshold_pct = threshold_pct
        self.protect_head = protect_head
        self.protect_tail = protect_tail
        self.max_context_tokens = max_context_tokens

    def needs_compression(self, messages: list[dict[str, str]]) -> bool:
        """Check if messages exceed the compression threshold."""
        total_tokens = count_message_tokens(messages)
        threshold = int(self.max_context_tokens * self.threshold_pct)
        return total_tokens > threshold

    async def compress(
        self,
        messages: list[dict[str, str]],
        summarize_fn: Any = None,
    ) -> list[dict[str, str]]:
        """Compress messages by summarizing the middle portion.

        Args:
            messages: Full message list.
            summarize_fn: Async function(prompt: str) -> str for summarization.
                         If None, middle turns are dropped without summary.

        Returns:
            Compressed message list.
        """
        if not self.needs_compression(messages):
            return messages

        total = len(messages)
        if total <= self.protect_head + self.protect_tail:
            return messages

        # Split into head, middle, tail
        head = messages[:self.protect_head]
        tail = messages[-self.protect_tail:]
        middle = messages[self.protect_head:total - self.protect_tail]

        if not middle:
            return messages

        # Sanitize orphaned tool_call/tool_result pairs in middle
        middle = self._sanitize_orphaned_pairs(middle)

        # Attempt summarization
        summary_text = None
        if summarize_fn:
            try:
                segment = self._format_segment(middle)
                prompt = COMPRESSION_PROMPT.format(segment=segment[:8000])
                summary_text = await summarize_fn(prompt)
            except Exception as e:
                logger.warning("Context summarization failed, dropping middle: %s", e)

        # Build compressed messages
        compressed = list(head)

        if summary_text:
            compressed.append({
                "role": "system",
                "content": f"[Conversation summary — {len(middle)} messages compressed]\n{summary_text}",
            })
        else:
            compressed.append({
                "role": "system",
                "content": f"[{len(middle)} earlier messages omitted for context management]",
            })

        compressed.extend(tail)

        before_tokens = count_message_tokens(messages)
        after_tokens = count_message_tokens(compressed)
        logger.info(
            "Context compressed: %d→%d messages, %d→%d tokens (%.0f%% reduction)",
            total, len(compressed),
            before_tokens, after_tokens,
            (1 - after_tokens / before_tokens) * 100 if before_tokens > 0 else 0,
        )

        return compressed

    def _format_segment(self, messages: list[dict[str, str]]) -> str:
        """Format messages into a readable segment for summarization."""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:500]
            lines.append(f"[{role}]: {content}")
        return "\n".join(lines)

    @staticmethod
    def _sanitize_orphaned_pairs(
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Remove orphaned tool_call/tool_result pairs.

        A tool_call without its matching tool result (or vice versa)
        causes API rejection. Remove both if either is missing.
        """
        # Collect tool_call IDs and tool result IDs
        call_ids: set[str] = set()
        result_ids: set[str] = set()

        for msg in messages:
            if msg.get("role") == "tool_call":
                fc = msg.get("_function_call")
                if fc and hasattr(fc, "call_id"):
                    call_ids.add(fc.call_id)
            elif msg.get("role") == "tool":
                tid = msg.get("tool_call_id", "")
                if tid:
                    result_ids.add(tid)

        # Find orphaned IDs
        orphaned = call_ids.symmetric_difference(result_ids)
        if not orphaned:
            return messages

        # Filter out messages with orphaned IDs
        cleaned = []
        for msg in messages:
            if msg.get("role") == "tool_call":
                fc = msg.get("_function_call")
                if fc and hasattr(fc, "call_id") and fc.call_id in orphaned:
                    continue
            elif msg.get("role") == "tool":
                if msg.get("tool_call_id", "") in orphaned:
                    continue
            cleaned.append(msg)

        if len(cleaned) < len(messages):
            logger.debug(
                "Sanitized %d orphaned tool pairs",
                len(messages) - len(cleaned),
            )

        return cleaned
