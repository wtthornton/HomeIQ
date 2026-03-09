"""Hybrid search combining FTS and vector similarity with RRF fusion.

Implements Reciprocal Rank Fusion (RRF) to combine PostgreSQL full-text search
with pgvector cosine similarity for optimal memory retrieval.

Based on the Memory Brain architecture for semantic memory retrieval.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from .decay import effective_confidence
from .models import Memory, MemoryType

if TYPE_CHECKING:
    from .embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


@dataclass
class MemorySearchResult:
    """Search result containing a memory and its relevance scores."""

    memory: Memory
    relevance_score: float
    fts_rank: int | None
    vector_rank: int | None


class MemorySearch:
    """Hybrid search combining FTS and vector similarity with RRF fusion.

    Uses Reciprocal Rank Fusion (RRF) to combine results from PostgreSQL
    full-text search and pgvector cosine similarity search. Applies
    confidence decay filtering to exclude stale memories.

    Example:
        >>> search = MemorySearch(session_factory, embedding_generator)
        >>> results = await search.search("turn on lights", limit=5)
        >>> for r in results:
        ...     print(f"{r.memory.content}: {r.relevance_score:.3f}")

    If embedding_generator is None, operates in FTS-only mode.
    """

    K = 60  # RRF constant (60 is standard)

    FTS_WEIGHT = 0.6
    VECTOR_WEIGHT = 0.4

    RECENCY_BOOST_DAYS = 30  # Memories within this window get a boost
    RECENCY_BOOST_FACTOR = 0.1  # Maximum recency boost added to RRF score
    CONFIDENCE_BOOST_FACTOR = 0.05  # Maximum confidence boost

    def __init__(
        self,
        session_factory: async_sessionmaker,
        embedding_generator: EmbeddingGenerator | None,
        fts_weight: float = 0.6,
        vector_weight: float = 0.4,
    ) -> None:
        """Initialize the hybrid search engine.

        Args:
            session_factory: SQLAlchemy async session factory.
            embedding_generator: Generator for query embeddings. If None,
                operates in FTS-only mode.
            fts_weight: Weight for FTS results in RRF fusion (default 0.6).
            vector_weight: Weight for vector results in RRF fusion (default 0.4).
        """
        self._session_factory = session_factory
        self._embedding_generator = embedding_generator
        self._fts_weight = fts_weight
        self._vector_weight = vector_weight

    async def search(
        self,
        query: str,
        memory_types: list[MemoryType] | None = None,
        entity_ids: list[str] | None = None,
        min_confidence: float = 0.3,
        limit: int = 10,
    ) -> list[MemorySearchResult]:
        """Execute hybrid search with RRF fusion and confidence filtering.

        Runs both FTS and vector similarity searches, combines results using
        Reciprocal Rank Fusion, then filters by effective confidence.

        Args:
            query: Search query string.
            memory_types: Filter to specific memory types (optional).
            entity_ids: Filter to memories associated with specific entities (optional).
            min_confidence: Minimum effective confidence after decay (default 0.3).
            limit: Maximum number of results to return (default 10).

        Returns:
            List of MemorySearchResult ordered by relevance score descending.
        """
        if not query.strip():
            return []

        import time

        start_time = time.perf_counter()

        filters = {
            "memory_types": memory_types,
            "entity_ids": entity_ids,
        }

        expanded_limit = limit * 3

        fts_results = await self._fts_search(query, filters, expanded_limit)
        logger.debug("FTS search returned %d results", len(fts_results))

        vector_results: list[tuple[int, int]] = []
        if self._embedding_generator is not None:
            try:
                query_embedding = await self._embedding_generator.generate(query)
                vector_results = await self._vector_search(
                    query_embedding, filters, expanded_limit
                )
                logger.debug("Vector search returned %d results", len(vector_results))
            except Exception as e:
                logger.warning("Vector search failed, using FTS-only: %s", e)

        if not fts_results and not vector_results:
            return []

        if vector_results:
            fused = self._reciprocal_rank_fusion(
                fts_results, vector_results, self._fts_weight, self._vector_weight
            )
        else:
            fused = [(mid, self._fts_weight / (self.K + rank)) for mid, rank in fts_results]

        memory_ids = [mid for mid, _ in fused]
        fts_ranks = {mid: rank for mid, rank in fts_results}
        vector_ranks = {mid: rank for mid, rank in vector_results}

        async with self._session_factory() as session:
            memories_query = text("""
                SELECT * FROM memory.memories
                WHERE id = ANY(:ids)
            """)
            result = await session.execute(memories_query, {"ids": memory_ids})
            rows = result.mappings().all()

            memories_by_id: dict[int, Memory] = {}
            for row in rows:
                memory = Memory(
                    id=row["id"],
                    content=row["content"],
                    memory_type=MemoryType(row["memory_type"]),
                    confidence=row["confidence"],
                    source_channel=row["source_channel"],
                    source_service=row["source_service"],
                    entity_ids=row["entity_ids"],
                    area_ids=row["area_ids"],
                    tags=row["tags"],
                    embedding=row["embedding"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    last_accessed=row["last_accessed"],
                    access_count=row["access_count"],
                    superseded_by=row["superseded_by"],
                    metadata_=row["metadata"],
                )
                memories_by_id[memory.id] = memory

        results: list[MemorySearchResult] = []
        now = datetime.now(UTC)

        for memory_id, rrf_score in fused:
            memory = memories_by_id.get(memory_id)
            if memory is None:
                continue

            eff_conf = effective_confidence(memory)
            if eff_conf < min_confidence:
                continue

            # Recency boost: newer memories scored higher for equal relevance
            recency_boost = 0.0
            if memory.updated_at:
                days_old = (now - memory.updated_at).total_seconds() / 86400
                if days_old < self.RECENCY_BOOST_DAYS:
                    recency_boost = self.RECENCY_BOOST_FACTOR * (
                        1.0 - days_old / self.RECENCY_BOOST_DAYS
                    )

            # Confidence boost: higher confidence memories ranked higher
            confidence_boost = self.CONFIDENCE_BOOST_FACTOR * eff_conf

            final_score = rrf_score + recency_boost + confidence_boost

            results.append(
                MemorySearchResult(
                    memory=memory,
                    relevance_score=final_score,
                    fts_rank=fts_ranks.get(memory_id),
                    vector_rank=vector_ranks.get(memory_id),
                )
            )

        # Re-sort by final boosted score
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        from . import metrics

        duration_ms = (time.perf_counter() - start_time) * 1000
        mode = "hybrid" if vector_results else "fts_only"
        metrics.emit_histogram("memory_search_latency_ms", duration_ms, {"mode": mode})
        metrics.emit("memory_search_result_count", len(results), {"mode": mode})

        return results[:limit]

    async def _fts_search(
        self, query: str, filters: dict, limit: int
    ) -> list[tuple[int, int]]:
        """Execute PostgreSQL full-text search.

        Uses to_tsvector and plainto_tsquery for robust text matching
        with ts_rank for relevance ordering.

        Args:
            query: Search query string.
            filters: Dict with memory_types and entity_ids filters.
            limit: Maximum number of results.

        Returns:
            List of (memory_id, rank) tuples ordered by relevance.
        """
        where_clauses = [
            "to_tsvector('english', content) @@ plainto_tsquery('english', :query)"
        ]
        params: dict = {"query": query, "limit": limit}

        if filters.get("memory_types"):
            where_clauses.append("memory_type = ANY(:memory_types)")
            params["memory_types"] = [mt.value for mt in filters["memory_types"]]

        if filters.get("entity_ids"):
            where_clauses.append("entity_ids && :entity_ids")
            params["entity_ids"] = filters["entity_ids"]

        where_sql = " AND ".join(where_clauses)

        sql = text(f"""
            SELECT id,
                   ROW_NUMBER() OVER (
                       ORDER BY ts_rank(
                           to_tsvector('english', content),
                           plainto_tsquery('english', :query)
                       ) DESC
                   ) as rank
            FROM memory.memories
            WHERE {where_sql}
            ORDER BY rank
            LIMIT :limit
        """)

        async with self._session_factory() as session:
            result = await session.execute(sql, params)
            rows = result.all()

        return [(row.id, row.rank) for row in rows]

    async def _vector_search(
        self, query_embedding: list[float], filters: dict, limit: int
    ) -> list[tuple[int, int]]:
        """Execute pgvector cosine similarity search.

        Uses the <=> operator for cosine distance (1 - cosine_similarity).
        Only searches memories that have embeddings.

        Args:
            query_embedding: Query vector from embedding generator.
            filters: Dict with memory_types and entity_ids filters.
            limit: Maximum number of results.

        Returns:
            List of (memory_id, rank) tuples ordered by similarity.
        """
        where_clauses = ["embedding IS NOT NULL"]
        params: dict = {"query_embedding": query_embedding, "limit": limit}

        if filters.get("memory_types"):
            where_clauses.append("memory_type = ANY(:memory_types)")
            params["memory_types"] = [mt.value for mt in filters["memory_types"]]

        if filters.get("entity_ids"):
            where_clauses.append("entity_ids && :entity_ids")
            params["entity_ids"] = filters["entity_ids"]

        where_sql = " AND ".join(where_clauses)

        sql = text(f"""
            SELECT id,
                   ROW_NUMBER() OVER (
                       ORDER BY embedding <=> :query_embedding
                   ) as rank
            FROM memory.memories
            WHERE {where_sql}
            ORDER BY rank
            LIMIT :limit
        """)

        async with self._session_factory() as session:
            result = await session.execute(sql, params)
            rows = result.all()

        return [(row.id, row.rank) for row in rows]

    def _reciprocal_rank_fusion(
        self,
        fts_results: list[tuple[int, int]],
        vector_results: list[tuple[int, int]],
        fts_weight: float,
        vector_weight: float,
    ) -> list[tuple[int, float]]:
        """Combine FTS and vector results using Reciprocal Rank Fusion.

        RRF formula: score = weight / (K + rank)

        This approach is robust to different score distributions between
        retrieval methods and doesn't require score normalization.

        Args:
            fts_results: List of (memory_id, rank) from FTS search.
            vector_results: List of (memory_id, rank) from vector search.
            fts_weight: Weight multiplier for FTS scores.
            vector_weight: Weight multiplier for vector scores.

        Returns:
            List of (memory_id, combined_score) sorted by score descending.
        """
        scores: dict[int, float] = {}

        for memory_id, rank in fts_results:
            rrf_score = fts_weight / (self.K + rank)
            scores[memory_id] = scores.get(memory_id, 0.0) + rrf_score

        for memory_id, rank in vector_results:
            rrf_score = vector_weight / (self.K + rank)
            scores[memory_id] = scores.get(memory_id, 0.0) + rrf_score

        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results
