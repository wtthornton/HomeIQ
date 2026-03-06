"""Memory injection for LLM prompts.

Formats retrieved memories into context blocks for LLM prompt injection,
with token budget management and graceful handling of empty results.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeiq_memory.models import MemoryType

if TYPE_CHECKING:
    from homeiq_memory.search import MemorySearch, MemorySearchResult

logger = logging.getLogger(__name__)


class MemoryInjector:
    """Formats memories for LLM prompt injection.

    Retrieves relevant memories via semantic search and formats them
    into a structured context block suitable for injection into LLM prompts.
    Respects token budgets by truncating lower-confidence memories first.

    Example:
        >>> injector = MemoryInjector(search=memory_search)
        >>> context = await injector.get_context("temperature preferences")
        >>> print(context)
        [Memory Context]
        - User prefers 72F evening temperature (preference, confidence: 0.85)
        - Morning routine starts at 6:30 AM (routine, confidence: 0.80)
    """

    DEFAULT_TOKEN_BUDGET = 2000  # ~500 words
    HEADER = "[Memory Context]"
    NO_MEMORIES_MESSAGE = "[No relevant memories]"

    def __init__(
        self,
        search: MemorySearch,
        token_budget: int = 2000,
        chars_per_token: int = 4,
        include_no_memories_message: bool = False,
    ) -> None:
        """Initialize the memory injector.

        Args:
            search: MemorySearch instance for hybrid memory retrieval.
            token_budget: Maximum estimated tokens for context block.
                         Defaults to 2000 (~500 words).
            chars_per_token: Characters per token estimate for budget calculation.
                            Defaults to 4 (conservative estimate).
            include_no_memories_message: If True, returns "[No relevant memories]"
                                        when no memories found. If False, returns
                                        empty string. Defaults to False.
        """
        self._search = search
        self._token_budget = token_budget
        self._chars_per_token = chars_per_token
        self._include_no_memories_message = include_no_memories_message

    async def get_context(
        self,
        query: str,
        memory_types: list[MemoryType] | None = None,
        entity_ids: list[str] | None = None,
        limit: int = 10,
        exclude_types: list[MemoryType] | None = None,
    ) -> str:
        """Retrieve and format memories as context for LLM injection.

        Args:
            query: Search query for semantic memory retrieval.
            memory_types: Filter to specific memory types. None includes all.
            entity_ids: Filter to memories involving specific entities.
            limit: Maximum number of memories to retrieve.
            exclude_types: Memory types to exclude from results.

        Returns:
            Formatted context block string, or empty string if no memories.

        Example:
            >>> context = await injector.get_context(
            ...     query="lighting preferences",
            ...     memory_types=[MemoryType.PREFERENCE, MemoryType.BOUNDARY],
            ... )
        """
        effective_types = self._apply_type_filters(memory_types, exclude_types)

        results = await self._search.search(
            query=query,
            memory_types=effective_types,
            entity_ids=entity_ids,
            limit=limit,
        )

        if not results:
            logger.debug("No memories found for query: %s", query[:50])
            if self._include_no_memories_message:
                return self.NO_MEMORIES_MESSAGE
            return ""

        logger.debug(
            "Retrieved %d memories for query: %s",
            len(results),
            query[:50],
        )

        return self.format_context_block(results)

    def _apply_type_filters(
        self,
        include_types: list[MemoryType] | None,
        exclude_types: list[MemoryType] | None,
    ) -> list[MemoryType] | None:
        """Apply include/exclude filters to memory types.

        Args:
            include_types: Types to include (None = all types).
            exclude_types: Types to exclude from the include set.

        Returns:
            Filtered list of memory types, or None for all types.
        """
        if exclude_types is None:
            return include_types

        if include_types is None:
            all_types = list(MemoryType)
            return [t for t in all_types if t not in exclude_types]

        return [t for t in include_types if t not in exclude_types]

    def format_memory(self, result: MemorySearchResult) -> str:
        """Format a single memory result for display.

        Args:
            result: Memory search result to format.

        Returns:
            Formatted string like:
            "- User prefers 72F (preference, confidence: 0.85)"

        Example:
            >>> formatted = injector.format_memory(result)
            >>> print(formatted)
            - User prefers 72F evening temperature (preference, confidence: 0.85)
        """
        memory = result.memory
        type_label = memory.memory_type.value

        base_format = f"- {memory.content} ({type_label}, confidence: {memory.confidence:.2f})"

        entity_context = self._format_entity_context(result)
        if entity_context:
            return f"{base_format} [{entity_context}]"

        return base_format

    def _format_entity_context(self, result: MemorySearchResult) -> str:
        """Format entity/area context for a memory.

        Args:
            result: Memory search result with optional entity/area IDs.

        Returns:
            Context string like "entities: light.living_room" or empty string.
        """
        memory = result.memory
        parts = []

        if memory.entity_ids:
            if len(memory.entity_ids) <= 2:
                parts.append(f"entities: {', '.join(memory.entity_ids)}")
            else:
                parts.append(f"entities: {', '.join(memory.entity_ids[:2])}...")

        if memory.area_ids:
            if len(memory.area_ids) <= 2:
                parts.append(f"areas: {', '.join(memory.area_ids)}")
            else:
                parts.append(f"areas: {', '.join(memory.area_ids[:2])}...")

        return "; ".join(parts)

    def format_context_block(self, results: list[MemorySearchResult]) -> str:
        """Format multiple memories into a context block.

        Combines formatted memories under the header, respecting the token
        budget by truncating lowest-confidence memories first.

        Args:
            results: List of memory search results to format.

        Returns:
            Complete context block with header and formatted memories.

        Example:
            >>> block = injector.format_context_block(results)
            >>> print(block)
            [Memory Context]
            - User prefers 72F (preference, confidence: 0.85)
            - Motion lights rejected (boundary, confidence: 0.95)
        """
        if not results:
            if self._include_no_memories_message:
                return self.NO_MEMORIES_MESSAGE
            return ""

        sorted_results = sorted(
            results,
            key=lambda r: (r.memory.confidence, r.relevance_score),
            reverse=True,
        )

        header_tokens = self._estimate_tokens(self.HEADER + "\n")
        available_budget = self._token_budget - header_tokens

        formatted_lines: list[str] = []
        current_tokens = 0

        for result in sorted_results:
            formatted = self.format_memory(result)
            line_tokens = self._estimate_tokens(formatted + "\n")

            if current_tokens + line_tokens > available_budget:
                logger.debug(
                    "Token budget reached after %d memories, truncating %d",
                    len(formatted_lines),
                    len(sorted_results) - len(formatted_lines),
                )
                break

            formatted_lines.append(formatted)
            current_tokens += line_tokens

        if not formatted_lines:
            logger.warning(
                "Token budget too small for any memories (budget=%d)",
                self._token_budget,
            )
            if self._include_no_memories_message:
                return self.NO_MEMORIES_MESSAGE
            return ""

        return f"{self.HEADER}\n" + "\n".join(formatted_lines)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses a simple character-based estimation. For more accurate
        token counting, consider using a tokenizer library.

        Args:
            text: Text to estimate tokens for.

        Returns:
            Estimated token count.
        """
        return len(text) // self._chars_per_token

    @property
    def token_budget(self) -> int:
        """Return the configured token budget."""
        return self._token_budget

    @token_budget.setter
    def token_budget(self, value: int) -> None:
        """Set a new token budget.

        Args:
            value: New token budget (must be positive).

        Raises:
            ValueError: If budget is not positive.
        """
        if value <= 0:
            raise ValueError(f"Token budget must be positive, got {value}")
        self._token_budget = value
