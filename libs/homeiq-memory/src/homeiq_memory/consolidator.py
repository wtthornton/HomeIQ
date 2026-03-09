"""Mem0-style memory consolidation for HomeIQ Memory Brain.

Implements the extract-consolidate-retrieve pattern to merge, update, skip,
or supersede memories based on semantic similarity and content analysis.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from .decay import effective_confidence, reinforce
from .models import Memory, MemoryArchive, MemoryType, SourceChannel

if TYPE_CHECKING:
    from .client import MemoryClient
    from .search import MemorySearch, MemorySearchResult

logger = logging.getLogger(__name__)


class ConsolidationAction(Enum):
    """Action taken during memory consolidation."""

    INSERT = "insert"
    REINFORCE = "reinforce"
    UPDATE = "update"
    SUPERSEDE = "supersede"
    SKIP = "skip"


@dataclass
class ConsolidationResult:
    """Result of a memory consolidation operation."""

    action: ConsolidationAction
    memory: Memory | None
    original_id: int | None
    reason: str


class MemoryConsolidator:
    """Mem0-style memory consolidation - merge/update/skip/supersede.

    Implements intelligent deduplication and consolidation of semantic memories
    based on vector similarity, content analysis, and recency.

    Example:
        >>> consolidator = MemoryConsolidator(client, search)
        >>> result = await consolidator.consolidate(
        ...     content="User prefers warm lighting",
        ...     memory_type=MemoryType.PREFERENCE,
        ...     source_channel=SourceChannel.IMPLICIT,
        ... )
        >>> print(f"Action: {result.action.value}, Memory ID: {result.memory.id}")
    """

    SIMILARITY_THRESHOLD = 0.85
    DUPLICATE_THRESHOLD = 0.95
    RECENT_WINDOW_HOURS = 24

    NEGATION_PATTERNS = re.compile(
        r"\b(not|never|don't|doesn't|didn't|won't|wouldn't|can't|cannot|"
        r"no longer|stopped|avoid|hate|dislike)\b",
        re.IGNORECASE,
    )

    AFFIRMATIVE_PATTERNS = re.compile(
        r"\b(always|loves?|likes?|prefers?|wants?|enjoys?|usually|often)\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        client: MemoryClient,
        search: MemorySearch,
    ) -> None:
        """Initialize the memory consolidator.

        Args:
            client: MemoryClient for CRUD operations.
            search: MemorySearch for finding similar memories.
        """
        self._client = client
        self._search = search

    async def consolidate(
        self,
        content: str,
        memory_type: MemoryType,
        source_channel: SourceChannel,
        entity_ids: list[str] | None = None,
        **kwargs: Any,
    ) -> ConsolidationResult:
        """Consolidate a new memory against existing memories.

        Finds similar memories and determines the appropriate action:
        - INSERT: No similar memories exist
        - REINFORCE: Very similar memory with same meaning
        - UPDATE: Similar memory with updated information
        - SUPERSEDE: Contradicts existing memory
        - SKIP: Duplicate of recent memory

        Args:
            content: The memory content text.
            memory_type: Classification of memory type.
            source_channel: How the memory was acquired.
            entity_ids: Optional list of related entity IDs for filtering.
            **kwargs: Additional arguments passed to save() (e.g., confidence,
                tags, area_ids, metadata, source_service).

        Returns:
            ConsolidationResult with action taken, resulting memory, and reason.

        Raises:
            RuntimeError: If client is not initialized.
        """
        similar_memories = await self._search.search(
            query=content,
            memory_types=[memory_type],
            entity_ids=entity_ids,
            min_confidence=0.1,
            limit=5,
        )

        similar_with_scores = await self._calculate_cosine_similarities(
            content, similar_memories
        )

        action, existing_memory, reason = await self._determine_action(
            content, similar_with_scores
        )

        logger.info(
            "Consolidation decision: action=%s reason=%s",
            action.value,
            reason,
        )
        from . import metrics

        metrics.emit("memory_consolidation_decisions", tags={"action": action.value})

        if action == ConsolidationAction.SKIP:
            return ConsolidationResult(
                action=action,
                memory=existing_memory,
                original_id=existing_memory.id if existing_memory else None,
                reason=reason,
            )

        if action == ConsolidationAction.INSERT:
            memory = await self._client.save(
                content=content,
                memory_type=memory_type,
                source_channel=source_channel,
                entity_ids=entity_ids,
                **kwargs,
            )
            logger.debug("Inserted new memory id=%d", memory.id)
            return ConsolidationResult(
                action=action,
                memory=memory,
                original_id=None,
                reason=reason,
            )

        if action == ConsolidationAction.REINFORCE:
            if existing_memory is None:
                raise RuntimeError("REINFORCE action requires existing memory")
            reinforced = reinforce(existing_memory, amount=0.1)
            memory = await self._client.update(
                memory_id=existing_memory.id,
                confidence=reinforced.confidence,
            )
            logger.debug(
                "Reinforced memory id=%d confidence=%.2f",
                existing_memory.id,
                reinforced.confidence,
            )
            return ConsolidationResult(
                action=action,
                memory=memory,
                original_id=existing_memory.id,
                reason=reason,
            )

        if action == ConsolidationAction.UPDATE:
            if existing_memory is None:
                raise RuntimeError("UPDATE action requires existing memory")
            merged_content = await self._merge_content(existing_memory.content, content)
            memory = await self._client.update(
                memory_id=existing_memory.id,
                content=merged_content,
            )
            logger.debug(
                "Updated memory id=%d with merged content",
                existing_memory.id,
            )
            return ConsolidationResult(
                action=action,
                memory=memory,
                original_id=existing_memory.id,
                reason=reason,
            )

        if action == ConsolidationAction.SUPERSEDE:
            if existing_memory is None:
                raise RuntimeError("SUPERSEDE action requires existing memory")
            memory = await self._client.supersede(
                old_id=existing_memory.id,
                new_content=content,
                memory_type=memory_type,
                source_channel=source_channel,
                entity_ids=entity_ids,
                **kwargs,
            )
            logger.debug(
                "Superseded memory id=%d with new id=%d",
                existing_memory.id,
                memory.id,
            )
            return ConsolidationResult(
                action=action,
                memory=memory,
                original_id=existing_memory.id,
                reason=reason,
            )

        raise RuntimeError(f"Unhandled consolidation action: {action}")

    async def _calculate_cosine_similarities(
        self,
        content: str,
        search_results: list[MemorySearchResult],
    ) -> list[tuple[MemorySearchResult, float]]:
        """Calculate actual cosine similarity scores for search results.

        The search module uses RRF fusion which doesn't give direct similarity.
        We need actual cosine similarity for threshold-based decisions.

        Args:
            content: Query content to compare against.
            search_results: Results from hybrid search.

        Returns:
            List of (search_result, cosine_similarity) tuples.
        """
        if not search_results:
            return []

        query_embedding = await self._client.embedding_generator.generate(content)

        results: list[tuple[MemorySearchResult, float]] = []
        for result in search_results:
            memory = result.memory
            if memory.embedding is None:
                results.append((result, 0.0))
                continue

            similarity = self._cosine_similarity(query_embedding, memory.embedding)
            results.append((result, similarity))

        return results

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            a: First vector.
            b: Second vector.

        Returns:
            Cosine similarity score between 0 and 1.
        """
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    async def _determine_action(
        self,
        candidate: str,
        similar_memories: list[tuple[MemorySearchResult, float]],
    ) -> tuple[ConsolidationAction, Memory | None, str]:
        """Determine consolidation action based on similarity analysis.

        Decision logic:
        1. If no similar memories -> INSERT
        2. If duplicate (>0.95 similarity) within 24h -> SKIP
        3. If very similar (>0.85) with same meaning -> REINFORCE
        4. If similar (>0.85) but contradicts -> SUPERSEDE
        5. If similar (>0.85) with updated info -> UPDATE
        6. Otherwise -> INSERT

        Args:
            candidate: The new memory content.
            similar_memories: List of (search_result, similarity) tuples.

        Returns:
            Tuple of (action, affected_memory, reason).
        """
        if not similar_memories:
            return (
                ConsolidationAction.INSERT,
                None,
                "No similar memories found",
            )

        now = datetime.now(UTC)
        recent_cutoff = now - timedelta(hours=self.RECENT_WINDOW_HOURS)

        for result, similarity in similar_memories:
            memory = result.memory

            if (
                similarity >= self.DUPLICATE_THRESHOLD
                and memory.created_at >= recent_cutoff
            ):
                return (
                    ConsolidationAction.SKIP,
                    memory,
                    f"Duplicate of recent memory (similarity={similarity:.2f})",
                )

            if similarity >= self.SIMILARITY_THRESHOLD:
                if self._is_contradiction(memory, candidate):
                    return (
                        ConsolidationAction.SUPERSEDE,
                        memory,
                        f"Contradicts existing memory (similarity={similarity:.2f})",
                    )

                if self._is_same_meaning(memory.content, candidate):
                    return (
                        ConsolidationAction.REINFORCE,
                        memory,
                        f"Reinforces existing memory (similarity={similarity:.2f})",
                    )

                return (
                    ConsolidationAction.UPDATE,
                    memory,
                    f"Updates existing memory with new details (similarity={similarity:.2f})",
                )

        return (
            ConsolidationAction.INSERT,
            None,
            "No sufficiently similar memories found",
        )

    def _is_contradiction(self, existing: Memory, candidate: str) -> bool:
        """Detect if candidate contradicts existing memory.

        Uses simple heuristics based on negation patterns and sentiment.

        Args:
            existing: The existing memory to check against.
            candidate: The new candidate content.

        Returns:
            True if candidate appears to contradict existing memory.
        """
        existing_has_negation = bool(self.NEGATION_PATTERNS.search(existing.content))
        candidate_has_negation = bool(self.NEGATION_PATTERNS.search(candidate))

        existing_has_affirmative = bool(
            self.AFFIRMATIVE_PATTERNS.search(existing.content)
        )
        candidate_has_affirmative = bool(self.AFFIRMATIVE_PATTERNS.search(candidate))

        return (existing_has_negation and candidate_has_affirmative) or (
            existing_has_affirmative and candidate_has_negation
        )

    def _is_same_meaning(self, existing_content: str, candidate: str) -> bool:
        """Detect if candidate has the same semantic meaning as existing.

        Simple heuristic: same sentiment polarity (both affirmative or both negative).

        Args:
            existing_content: Content of existing memory.
            candidate: New candidate content.

        Returns:
            True if both appear to express the same sentiment/meaning.
        """
        existing_has_negation = bool(self.NEGATION_PATTERNS.search(existing_content))
        candidate_has_negation = bool(self.NEGATION_PATTERNS.search(candidate))

        return existing_has_negation == candidate_has_negation  # noqa: SIM103

    async def _merge_content(self, existing: str, new: str) -> str:
        """Merge existing and new content using semantic similarity.

        Decision logic:
        - Similarity > 0.9: keep newer (more recent = more accurate)
        - Similarity 0.7-0.9: extract unique facts from both
        - Similarity < 0.7: concatenate (they cover different aspects)

        Args:
            existing: Existing memory content.
            new: New content to merge.

        Returns:
            Merged content string.
        """
        # Calculate similarity for merge strategy
        try:
            existing_emb = await self._client.embedding_generator.generate(existing)
            new_emb = await self._client.embedding_generator.generate(new)
            similarity = self._cosine_similarity(existing_emb, new_emb)
        except Exception:
            # Fallback: prefer newer content
            return new if len(new) >= len(existing) else f"{existing}. {new}"

        if similarity > 0.9:
            # Very similar — keep newer (more recent = more accurate)
            logger.debug(
                "Merge: keeping newer content (similarity=%.2f)", similarity
            )
            return new

        if similarity >= 0.7:
            # Moderately similar — deduplicate by keeping the more detailed version
            # and appending any unique info from the other
            logger.debug(
                "Merge: combining content (similarity=%.2f)", similarity
            )
            # Use the longer as base, append the shorter's unique info
            if len(new) >= len(existing):
                return new
            return f"{existing}. Additionally: {new}"

        # Low similarity — different aspects, concatenate both
        logger.debug(
            "Merge: concatenating different aspects (similarity=%.2f)", similarity
        )
        return f"{existing}. {new}"

    async def run_garbage_collection(self, archive_threshold: float = 0.15) -> int:
        """Archive memories below effective confidence threshold.

        Finds all memories with effective_confidence below threshold and
        moves them to the archive table.

        Args:
            archive_threshold: Minimum effective confidence to remain active.

        Returns:
            Count of memories archived.
        """
        archived_count = 0

        async with self._client._get_session() as session:
            stmt = select(Memory).where(Memory.superseded_by.is_(None))
            result = await session.execute(stmt)
            memories = result.scalars().all()

            for memory in memories:
                eff_conf = effective_confidence(memory)
                if eff_conf < archive_threshold:
                    archive = MemoryArchive(
                        original_id=memory.id,
                        content=memory.content,
                        memory_type=memory.memory_type,
                        confidence=memory.confidence,
                        source_channel=memory.source_channel,
                        source_service=memory.source_service,
                        entity_ids=memory.entity_ids,
                        area_ids=memory.area_ids,
                        tags=memory.tags,
                        embedding=memory.embedding,
                        created_at=memory.created_at,
                        updated_at=memory.updated_at,
                        last_accessed=memory.last_accessed,
                        access_count=memory.access_count,
                        superseded_by=memory.superseded_by,
                        metadata_=memory.metadata_,
                        archive_reason="garbage_collection",
                    )
                    session.add(archive)
                    await session.delete(memory)
                    archived_count += 1
                    logger.debug(
                        "Archived memory id=%d effective_confidence=%.2f",
                        memory.id,
                        eff_conf,
                    )

        logger.info(
            "Garbage collection complete: archived %d memories below %.2f confidence",
            archived_count,
            archive_threshold,
        )
        from . import metrics

        metrics.emit("memory_decay_archived_count", archived_count)
        return archived_count

    async def detect_contradictions(self) -> list[tuple[Memory, Memory]]:
        """Find pairs of active memories that may contradict each other.

        Scans active memories for high similarity pairs with conflicting
        content patterns.

        Returns:
            List of (memory1, memory2) pairs that appear to contradict.
        """
        contradictions: list[tuple[Memory, Memory]] = []

        async with self._client._get_session() as session:
            stmt = select(Memory).where(Memory.superseded_by.is_(None))
            result = await session.execute(stmt)
            memories = list(result.scalars().all())

        for i, memory1 in enumerate(memories):
            if memory1.embedding is None:
                continue

            for memory2 in memories[i + 1 :]:
                if memory2.embedding is None:
                    continue

                if memory1.memory_type != memory2.memory_type:
                    continue

                similarity = self._cosine_similarity(
                    list(memory1.embedding), list(memory2.embedding)
                )

                if (
                    similarity >= self.SIMILARITY_THRESHOLD
                    and self._is_contradiction(memory1, memory2.content)
                ):
                    contradictions.append((memory1, memory2))
                    logger.debug(
                        "Found contradiction: memory %d vs %d (similarity=%.2f)",
                        memory1.id,
                        memory2.id,
                        similarity,
                    )

        logger.info("Contradiction detection found %d pairs", len(contradictions))
        return contradictions
