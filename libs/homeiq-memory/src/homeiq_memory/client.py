"""Async client for memory CRUD operations.

Provides the core interface for storing, retrieving, updating, and deleting
semantic memories with vector embeddings and confidence decay.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .embeddings import EmbeddingGenerator
from .models import Base, Memory, MemoryArchive, MemoryType, SourceChannel

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from .search import MemorySearch, MemorySearchResult

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "postgresql+asyncpg://homeiq:homeiq@localhost:5432/homeiq"


class MemoryClient:
    """Async client for memory CRUD operations.

    Provides methods for saving, retrieving, updating, and deleting memories
    with automatic embedding generation and confidence management.

    Example:
        >>> client = MemoryClient()
        >>> await client.initialize()
        >>> memory = await client.save(
        ...     content="User prefers warm lighting in evenings",
        ...     memory_type=MemoryType.PREFERENCE,
        ...     source_channel=SourceChannel.IMPLICIT,
        ... )
        >>> print(memory.id)
    """

    def __init__(
        self,
        database_url: str | None = None,
        embedding_generator: EmbeddingGenerator | None = None,
        pool_size: int = 5,
        max_overflow: int = 3,
    ) -> None:
        """Initialize the memory client.

        Args:
            database_url: PostgreSQL connection URL. Falls back to
                MEMORY_DATABASE_URL env var, then DATABASE_URL, then default.
            embedding_generator: Optional custom embedding generator.
                Creates default EmbeddingGenerator if not provided.
            pool_size: Connection pool size (default: 5).
            max_overflow: Max overflow connections (default: 3).
        """
        self._url = self._resolve_url(database_url)
        self._embedding_generator = embedding_generator
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker[AsyncSession] | None = None
        self._available = False

    def _resolve_url(self, explicit_url: str | None) -> str:
        """Resolve database URL from explicit param or environment."""
        if explicit_url and explicit_url.strip():
            return explicit_url
        return (
            os.environ.get("MEMORY_DATABASE_URL")
            or os.environ.get("DATABASE_URL")
            or DEFAULT_DATABASE_URL
        )

    @property
    def embedding_generator(self) -> EmbeddingGenerator:
        """Get or lazily create the embedding generator."""
        if self._embedding_generator is None:
            self._embedding_generator = EmbeddingGenerator()
        return self._embedding_generator

    async def initialize(self, create_tables: bool = False) -> bool:
        """Initialize database connection and optionally create tables.

        Args:
            create_tables: If True, creates tables using Base.metadata.
                Should be False when using Alembic migrations.

        Returns:
            True if initialization succeeded, False otherwise.
        """
        try:
            self._engine = create_async_engine(
                self._url,
                pool_size=self._pool_size,
                max_overflow=self._max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False,
            )

            self._session_maker = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )

            async with self._engine.begin() as conn:
                from sqlalchemy import text

                await conn.execute(text("SELECT 1"))

            if create_tables:
                async with self._engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)

            self._available = True
            logger.info("MemoryClient initialized successfully")
            return True

        except Exception as e:
            logger.error("MemoryClient initialization failed: %s", e, exc_info=True)
            self._available = False
            return False

    async def close(self) -> None:
        """Close database connections and clean up."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_maker = None
            self._available = False
            logger.info("MemoryClient connections closed")

    @asynccontextmanager
    async def _get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Create and yield an async database session.

        Raises:
            RuntimeError: If client is not initialized.
        """
        if not self._available or self._session_maker is None:
            raise RuntimeError(
                "MemoryClient not initialized. Call initialize() first."
            )
        async with self._session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @property
    def available(self) -> bool:
        """Whether the client is initialized and available."""
        return self._available

    async def preload_embeddings(self) -> bool:
        """Preload the embedding model at startup.

        Should be called during service lifespan startup after initialize().
        Falls back to lazy loading if preload fails.

        Returns:
            True if model loaded successfully, False otherwise.
        """
        try:
            return await self.embedding_generator.preload()
        except Exception as e:
            logger.warning("Embedding preload failed, will lazy-load: %s", e)
            return False

    async def save(
        self,
        content: str,
        memory_type: MemoryType,
        source_channel: SourceChannel,
        source_service: str | None = None,
        entity_ids: list[str] | None = None,
        area_ids: list[str] | None = None,
        domain: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        confidence: float = 0.5,
    ) -> Memory:
        """Save a new memory to the database.

        Args:
            content: The memory content text.
            memory_type: Classification of memory (behavioral, preference, etc.).
            source_channel: How the memory was acquired (explicit, implicit, etc.).
            source_service: Optional service name that created the memory.
            entity_ids: Optional list of related Home Assistant entity IDs.
            area_ids: Optional list of related Home Assistant area IDs.
            domain: Optional semantic domain (e.g., "lighting", "climate").
                Auto-classified from entity_ids if not provided.
            tags: Optional list of tags for categorization.
            metadata: Optional JSON metadata dictionary.
            confidence: Initial confidence score (0.0-1.0, default 0.5).

        Returns:
            The created Memory instance with ID populated.

        Raises:
            RuntimeError: If client is not initialized.
            ValueError: If content is empty.
        """
        if not content or not content.strip():
            raise ValueError("Memory content cannot be empty")

        if domain is None:
            from .domains import classify_domain

            domain = classify_domain(entity_ids)

        embedding = await self.embedding_generator.generate(content)

        memory = Memory(
            content=content.strip(),
            memory_type=memory_type,
            source_channel=source_channel,
            source_service=source_service,
            entity_ids=entity_ids,
            area_ids=area_ids,
            domain=domain,
            tags=tags,
            embedding=embedding,
            confidence=confidence,
            metadata_=metadata,
        )

        async with self._get_session() as session:
            session.add(memory)
            await session.flush()
            await session.refresh(memory)
            logger.debug(
                "Saved memory id=%d type=%s confidence=%.2f",
                memory.id,
                memory_type.value,
                confidence,
            )
            from . import metrics

            metrics.emit("memory_save_count", tags={"type": memory_type.value, "source": source_channel.value})
            return memory

    async def get(self, memory_id: int) -> Memory | None:
        """Retrieve a memory by its ID.

        Args:
            memory_id: The memory's primary key ID.

        Returns:
            The Memory instance if found, None otherwise.

        Raises:
            RuntimeError: If client is not initialized.
        """
        async with self._get_session() as session:
            stmt = select(Memory).where(Memory.id == memory_id)
            result = await session.execute(stmt)
            memory = result.scalar_one_or_none()
            if memory:
                logger.debug("Retrieved memory id=%d", memory_id)
            else:
                logger.debug("Memory id=%d not found", memory_id)
            return memory

    async def update(
        self,
        memory_id: int,
        content: str | None = None,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Memory | None:
        """Update an existing memory.

        Args:
            memory_id: The memory's primary key ID.
            content: New content text. Re-generates embedding if provided.
            confidence: New confidence score (0.0-1.0).
            metadata: New metadata dictionary (replaces existing).

        Returns:
            The updated Memory instance, or None if not found.

        Raises:
            RuntimeError: If client is not initialized.
        """
        async with self._get_session() as session:
            stmt = select(Memory).where(Memory.id == memory_id)
            result = await session.execute(stmt)
            memory = result.scalar_one_or_none()

            if memory is None:
                logger.debug("Memory id=%d not found for update", memory_id)
                return None

            if content is not None:
                content = content.strip()
                if not content:
                    raise ValueError("Memory content cannot be empty")
                memory.content = content
                memory.embedding = await self.embedding_generator.generate(content)

            if confidence is not None:
                memory.confidence = confidence

            if metadata is not None:
                memory.metadata_ = metadata

            memory.updated_at = datetime.now(UTC)

            await session.flush()
            await session.refresh(memory)
            logger.debug("Updated memory id=%d", memory_id)
            return memory

    async def delete(self, memory_id: int, reason: str = "manual") -> bool:
        """Soft delete a memory by moving it to the archive.

        Args:
            memory_id: The memory's primary key ID.
            reason: Reason for archival (e.g., "manual", "decay", "superseded").

        Returns:
            True if the memory was archived and deleted, False if not found.

        Raises:
            RuntimeError: If client is not initialized.
        """
        async with self._get_session() as session:
            stmt = select(Memory).where(Memory.id == memory_id)
            result = await session.execute(stmt)
            memory = result.scalar_one_or_none()

            if memory is None:
                logger.debug("Memory id=%d not found for deletion", memory_id)
                return False

            archive = MemoryArchive(
                original_id=memory.id,
                content=memory.content,
                memory_type=memory.memory_type,
                confidence=memory.confidence,
                source_channel=memory.source_channel,
                source_service=memory.source_service,
                entity_ids=memory.entity_ids,
                area_ids=memory.area_ids,
                domain=memory.domain,
                tags=memory.tags,
                embedding=memory.embedding,
                created_at=memory.created_at,
                updated_at=memory.updated_at,
                last_accessed=memory.last_accessed,
                access_count=memory.access_count,
                superseded_by=memory.superseded_by,
                metadata_=memory.metadata_,
                archive_reason=reason,
            )
            session.add(archive)

            delete_stmt = delete(Memory).where(Memory.id == memory_id)
            await session.execute(delete_stmt)

            logger.debug(
                "Archived and deleted memory id=%d reason=%s",
                memory_id,
                reason,
            )
            from . import metrics

            metrics.emit("memory_delete_count", tags={"reason": reason})
            return True

    async def supersede(
        self,
        old_id: int,
        new_content: str,
        memory_type: MemoryType,
        source_channel: SourceChannel,
        **kwargs: Any,
    ) -> Memory:
        """Replace an old memory with a new one, maintaining the chain.

        Creates a new memory and marks the old one as superseded by pointing
        its superseded_by field to the new memory's ID.

        Args:
            old_id: The ID of the memory being superseded.
            new_content: Content for the new memory.
            memory_type: Type classification for the new memory.
            source_channel: Source channel for the new memory.
            **kwargs: Additional arguments passed to save() (e.g., confidence,
                tags, entity_ids, area_ids, metadata, source_service).

        Returns:
            The newly created Memory instance.

        Raises:
            RuntimeError: If client is not initialized.
            ValueError: If the old memory is not found.
        """
        async with self._get_session() as session:
            stmt = select(Memory).where(Memory.id == old_id)
            result = await session.execute(stmt)
            old_memory = result.scalar_one_or_none()

            if old_memory is None:
                raise ValueError(f"Memory id={old_id} not found for supersession")

            embedding = await self.embedding_generator.generate(new_content.strip())

            domain = kwargs.get("domain")
            if domain is None:
                from .domains import classify_domain

                domain = classify_domain(kwargs.get("entity_ids"))

            new_memory = Memory(
                content=new_content.strip(),
                memory_type=memory_type,
                source_channel=source_channel,
                source_service=kwargs.get("source_service"),
                entity_ids=kwargs.get("entity_ids"),
                area_ids=kwargs.get("area_ids"),
                domain=domain,
                tags=kwargs.get("tags"),
                embedding=embedding,
                confidence=kwargs.get("confidence", 0.5),
                metadata_=kwargs.get("metadata"),
            )
            session.add(new_memory)
            await session.flush()

            update_stmt = (
                update(Memory)
                .where(Memory.id == old_id)
                .values(superseded_by=new_memory.id)
            )
            await session.execute(update_stmt)

            await session.refresh(new_memory)
            logger.debug(
                "Created memory id=%d superseding id=%d",
                new_memory.id,
                old_id,
            )
            return new_memory

    async def search_with_fallback(
        self,
        search: MemorySearch,
        query: str,
        memory_types: list[MemoryType] | None = None,
        entity_ids: list[str] | None = None,
        min_confidence: float = 0.3,
        limit: int = 10,
    ) -> list[MemorySearchResult]:
        """Search memories with graceful degradation.

        Attempts to search memories but returns an empty list on failure
        instead of raising an exception. This allows callers to continue
        functioning even when the memory system is unavailable.

        Args:
            search: MemorySearch instance to use for searching.
            query: Search query string.
            memory_types: Filter to specific memory types (optional).
            entity_ids: Filter to memories associated with specific entities.
            min_confidence: Minimum effective confidence after decay.
            limit: Maximum number of results to return.

        Returns:
            List of MemorySearchResult, or empty list if search fails.
        """
        try:
            return await search.search(
                query=query,
                memory_types=memory_types,
                entity_ids=entity_ids,
                min_confidence=min_confidence,
                limit=limit,
            )
        except Exception as e:
            logger.warning("Memory search failed, proceeding without: %s", e)
            return []

    async def save_with_fallback(
        self,
        content: str,
        memory_type: MemoryType,
        source_channel: SourceChannel,
        **kwargs,
    ) -> Memory | None:
        """Save a memory with graceful degradation.

        Attempts to save a memory but returns None on failure instead of
        raising an exception. Useful for non-critical memory captures.

        Args:
            content: The memory content text.
            memory_type: Classification of memory.
            source_channel: How the memory was acquired.
            **kwargs: Additional arguments passed to save().

        Returns:
            The created Memory instance, or None if save failed.
        """
        try:
            return await self.save(
                content=content,
                memory_type=memory_type,
                source_channel=source_channel,
                **kwargs,
            )
        except Exception as e:
            logger.warning("Memory save failed, continuing without: %s", e)
            return None
