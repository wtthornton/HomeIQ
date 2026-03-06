"""Memory system health checks and self-healing.

Provides health monitoring, diagnostics, and self-repair capabilities
for the memory system including database connectivity, pgvector extension,
embedding model status, and FTS index integrity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

if TYPE_CHECKING:
    from .client import MemoryClient

__all__ = ["HealthStatus", "MemoryHealthCheck"]

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health status report for the memory system."""

    healthy: bool
    database_connected: bool
    pgvector_available: bool
    embedding_model_loaded: bool
    fts_index_healthy: bool
    last_check: datetime
    issues: list[str] = field(default_factory=list)
    repairs_attempted: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "healthy": self.healthy,
            "database_connected": self.database_connected,
            "pgvector_available": self.pgvector_available,
            "embedding_model_loaded": self.embedding_model_loaded,
            "fts_index_healthy": self.fts_index_healthy,
            "last_check": self.last_check.isoformat(),
            "issues": self.issues,
            "repairs_attempted": self.repairs_attempted,
        }


class MemoryHealthCheck:
    """Health monitoring and self-healing for memory system.

    Performs health checks on all memory system components and attempts
    automatic repairs where safe to do so.

    Example:
        >>> client = MemoryClient()
        >>> await client.initialize()
        >>> health = MemoryHealthCheck(client)
        >>> status = await health.check_health()
        >>> if not status.healthy:
        ...     print(f"Issues: {status.issues}")
    """

    def __init__(self, memory_client: MemoryClient) -> None:
        """Initialize the health checker.

        Args:
            memory_client: An initialized MemoryClient instance.
        """
        self.memory = memory_client
        self.last_status: HealthStatus | None = None

    async def check_health(self, auto_repair: bool = True) -> HealthStatus:
        """Run all health checks and optionally attempt repairs.

        Args:
            auto_repair: If True, attempt to repair detected issues.

        Returns:
            HealthStatus with check results and any repair attempts.
        """
        issues: list[str] = []
        repairs: list[str] = []

        db_ok = await self._check_database()
        if not db_ok:
            issues.append("Database connection failed")

        pgvector_ok = False
        fts_ok = False

        if db_ok:
            pgvector_ok = await self._check_pgvector()
            if not pgvector_ok:
                issues.append("pgvector extension not available")

            fts_ok = await self._check_fts_index()
            if not fts_ok:
                issues.append("FTS index may need rebuild")
                if auto_repair:
                    if await self._repair_fts_index():
                        repairs.append("FTS index rebuilt")
                        fts_ok = True
                    else:
                        repairs.append("FTS index rebuild failed")

        embedding_ok = self._check_embedding_model()
        if not embedding_ok:
            issues.append("Embedding model not loaded")

        self.last_status = HealthStatus(
            healthy=len(issues) == 0 or (len(issues) == len(repairs)),
            database_connected=db_ok,
            pgvector_available=pgvector_ok,
            embedding_model_loaded=embedding_ok,
            fts_index_healthy=fts_ok,
            last_check=datetime.now(UTC),
            issues=issues,
            repairs_attempted=repairs,
        )

        if self.last_status.healthy:
            logger.info("Memory system health check passed")
        else:
            logger.warning(
                "Memory system health check found issues: %s",
                ", ".join(issues),
            )

        return self.last_status

    async def _check_database(self) -> bool:
        """Check database connectivity.

        Returns:
            True if database is connected and responsive.
        """
        if not self.memory.available:
            return False

        try:
            async with self.memory._get_session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("Database health check failed: %s", e)
            return False

    async def _check_pgvector(self) -> bool:
        """Check if pgvector extension is available.

        Returns:
            True if pgvector extension is installed and functional.
        """
        try:
            async with self.memory._get_session() as session:
                result = await session.execute(
                    text(
                        "SELECT EXISTS("
                        "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
                        ")"
                    )
                )
                row = result.scalar()
                return bool(row)
        except Exception as e:
            logger.error("pgvector check failed: %s", e)
            return False

    def _check_embedding_model(self) -> bool:
        """Check if embedding model is loaded or loadable.

        Returns:
            True if embedding model is available.
        """
        try:
            generator = self.memory.embedding_generator
            return generator is not None
        except Exception as e:
            logger.error("Embedding model check failed: %s", e)
            return False

    async def _check_fts_index(self) -> bool:
        """Check if FTS index exists and is valid.

        Returns:
            True if FTS index is healthy.
        """
        try:
            async with self.memory._get_session() as session:
                result = await session.execute(
                    text(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE schemaname = 'memory' "
                        "AND tablename = 'memories' "
                        "AND indexdef LIKE '%tsvector%'"
                    )
                )
                rows = result.fetchall()
                return len(rows) > 0
        except Exception as e:
            logger.error("FTS index check failed: %s", e)
            return False

    async def _repair_fts_index(self) -> bool:
        """Rebuild FTS index if unhealthy.

        Returns:
            True if repair succeeded.
        """
        try:
            async with self.memory._get_session() as session:
                result = await session.execute(
                    text(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE schemaname = 'memory' "
                        "AND tablename = 'memories' "
                        "AND indexdef LIKE '%tsvector%'"
                    )
                )
                rows = result.fetchall()

                for row in rows:
                    index_name = row[0]
                    logger.info("Rebuilding FTS index: %s", index_name)
                    await session.execute(
                        text(f"REINDEX INDEX memory.{index_name}")  # noqa: S608
                    )

            logger.info("FTS index rebuild completed")
            return True
        except Exception as e:
            logger.error("FTS index rebuild failed: %s", e)
            return False

    async def backfill_embeddings(self, batch_size: int = 50) -> int:
        """Generate embeddings for memories with NULL embeddings.

        Finds memories without embeddings and generates them in batches.
        This is useful for recovery after embedding failures or when
        upgrading embedding models.

        Args:
            batch_size: Number of memories to process per batch.

        Returns:
            Count of memories that had embeddings generated.
        """
        filled_count = 0

        try:
            async with self.memory._get_session() as session:
                result = await session.execute(
                    text(
                        "SELECT id, content FROM memory.memories "
                        "WHERE embedding IS NULL "
                        "ORDER BY created_at DESC"
                    )
                )
                rows = result.fetchall()

            if not rows:
                logger.info("No memories need embedding backfill")
                return 0

            logger.info("Found %d memories needing embeddings", len(rows))

            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                contents = [row[1] for row in batch]

                try:
                    embeddings = await self.memory.embedding_generator.generate_batch(
                        contents
                    )

                    async with self.memory._get_session() as session:
                        for (memory_id, _), embedding in zip(
                            batch, embeddings, strict=True
                        ):
                            await session.execute(
                                text(
                                    "UPDATE memory.memories "
                                    "SET embedding = :embedding "
                                    "WHERE id = :id"
                                ),
                                {"id": memory_id, "embedding": embedding},
                            )
                        filled_count += len(batch)

                    logger.debug(
                        "Backfilled embeddings for batch %d-%d",
                        i,
                        i + len(batch),
                    )

                except Exception as e:
                    logger.error("Embedding backfill batch failed: %s", e)
                    continue

            logger.info("Embedding backfill complete: %d memories filled", filled_count)

        except Exception as e:
            logger.error("Embedding backfill failed: %s", e)

        return filled_count

    async def get_stats(self) -> dict[str, int]:
        """Get memory system statistics.

        Returns:
            Dictionary with memory counts and health metrics.
        """
        stats: dict[str, int] = {
            "total_memories": 0,
            "memories_with_embeddings": 0,
            "memories_without_embeddings": 0,
            "archived_memories": 0,
            "superseded_memories": 0,
        }

        if not self.memory.available:
            return stats

        try:
            async with self.memory._get_session() as session:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM memory.memories")
                )
                stats["total_memories"] = result.scalar() or 0

                result = await session.execute(
                    text(
                        "SELECT COUNT(*) FROM memory.memories "
                        "WHERE embedding IS NOT NULL"
                    )
                )
                stats["memories_with_embeddings"] = result.scalar() or 0

                stats["memories_without_embeddings"] = (
                    stats["total_memories"] - stats["memories_with_embeddings"]
                )

                result = await session.execute(
                    text("SELECT COUNT(*) FROM memory.memory_archive")
                )
                stats["archived_memories"] = result.scalar() or 0

                result = await session.execute(
                    text(
                        "SELECT COUNT(*) FROM memory.memories "
                        "WHERE superseded_by IS NOT NULL"
                    )
                )
                stats["superseded_memories"] = result.scalar() or 0

        except Exception as e:
            logger.error("Failed to get memory stats: %s", e)

        return stats
