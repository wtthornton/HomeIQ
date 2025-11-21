"""
Embedding Cache Manager

Epic AI-4, Story AI4.1: Device Embedding Generation
In-memory cache for fast embedding access during multi-hop detection.

Features:
- LRU eviction when cache full
- Batch loading by area
- Memory limit enforcement (200MB default)
"""

import logging

import numpy as np
import torch

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    In-memory embedding cache for fast access during detection.

    Story AI4.6: Performance Optimization
    Context7: Minimize I/O, maximize cache hits

    Usage:
        >>> cache = EmbeddingCache(db_session, max_cache_mb=200)
        >>> embeddings = cache.load_embeddings(["light.kitchen", "sensor.motion"])
        >>> cache.load_area("kitchen")  # Batch load entire area
    """

    EMBEDDING_SIZE_BYTES = 384 * 4  # 384 floats * 4 bytes = 1536 bytes

    def __init__(self, db_session, max_cache_mb: int = 200):
        """
        Initialize embedding cache.

        Args:
            db_session: SQLite database session
            max_cache_mb: Maximum cache size in megabytes
        """
        self.db = db_session
        self.max_cache_mb = max_cache_mb
        self.max_cache_entries = int((max_cache_mb * 1024 * 1024) / self.EMBEDDING_SIZE_BYTES)

        self._cache: dict[str, torch.Tensor] = {}
        self._loaded_areas: set[str] = set()
        self._access_order: list[str] = []  # For LRU eviction

        logger.info(
            f"Embedding cache initialized: max {max_cache_mb}MB "
            f"(~{self.max_cache_entries} embeddings)",
        )

    def load_embeddings(
        self,
        entity_ids: list[str],
        convert_to_tensor: bool = True,
    ) -> dict[str, torch.Tensor]:
        """
        Load embeddings with intelligent caching.

        Strategy:
        1. Check in-memory cache first
        2. Load from database if miss
        3. Convert to tensors for GPU compatibility
        4. LRU eviction if cache full

        Args:
            entity_ids: List of entity IDs to load
            convert_to_tensor: Convert to PyTorch tensors

        Returns:
            Dict mapping entity_id to embedding tensor
        """
        embeddings = {}
        to_load = []

        # Check cache first
        for entity_id in entity_ids:
            if entity_id in self._cache:
                embeddings[entity_id] = self._cache[entity_id]
                self._update_access(entity_id)  # Update LRU
            else:
                to_load.append(entity_id)

        # Load missing embeddings from database
        if to_load:
            loaded = self._load_from_db(to_load)

            for entity_id, embedding_bytes in loaded.items():
                # Convert bytes to numpy array
                embedding_np = np.frombuffer(embedding_bytes, dtype=np.float32)

                # Convert to tensor if requested
                embedding = torch.from_numpy(embedding_np) if convert_to_tensor else embedding_np

                # Cache if space available (with LRU eviction)
                self._add_to_cache(entity_id, embedding)

                embeddings[entity_id] = embedding

        logger.debug(
            f"Embedding cache: {len(self._cache)} cached, "
            f"{len(to_load)} loaded from DB, "
            f"hit rate: {len(embeddings) - len(to_load)}/{len(entity_ids)}",
        )

        return embeddings

    def load_area(self, area_id: str):
        """
        Batch load all embeddings for an area.

        Performance optimization: Load entire area at once instead of
        individual device lookups.

        Args:
            area_id: Area identifier (e.g., "kitchen", "living_room")
        """
        if area_id in self._loaded_areas:
            logger.debug(f"Area '{area_id}' already loaded (skipping)")
            return

        # Get all entity_ids in area
        results = self.db.execute(
            """
            SELECT de.entity_id, de.embedding
            FROM device_embeddings de
            JOIN entities e ON de.entity_id = e.entity_id
            WHERE e.area_id = ?
            """,
            (area_id,),
        ).fetchall()

        # Cache all (with LRU eviction if needed)
        loaded_count = 0
        for entity_id, embedding_bytes in results:
            if entity_id not in self._cache:
                embedding_np = np.frombuffer(embedding_bytes, dtype=np.float32)
                embedding = torch.from_numpy(embedding_np)
                self._add_to_cache(entity_id, embedding)
                loaded_count += 1

        self._loaded_areas.add(area_id)
        logger.info(f"Loaded {loaded_count} embeddings for area '{area_id}'")

    def _load_from_db(self, entity_ids: list[str]) -> dict[str, bytes]:
        """
        Load embeddings from database.

        Args:
            entity_ids: List of entity IDs

        Returns:
            Dict mapping entity_id to embedding bytes
        """
        placeholders = ",".join(["?" for _ in entity_ids])
        results = self.db.execute(
            f"SELECT entity_id, embedding FROM device_embeddings WHERE entity_id IN ({placeholders})",
            entity_ids,
        ).fetchall()

        return dict(results)

    def _add_to_cache(self, entity_id: str, embedding: torch.Tensor):
        """
        Add embedding to cache with LRU eviction.

        Args:
            entity_id: Entity identifier
            embedding: Embedding tensor
        """
        # Evict if cache full
        while len(self._cache) >= self.max_cache_entries:
            self._evict_lru()

        # Add to cache
        self._cache[entity_id] = embedding
        self._access_order.append(entity_id)

    def _update_access(self, entity_id: str):
        """
        Update access order for LRU tracking.

        Args:
            entity_id: Entity identifier
        """
        if entity_id in self._access_order:
            self._access_order.remove(entity_id)
        self._access_order.append(entity_id)

    def _evict_lru(self):
        """Evict least recently used embedding."""
        if self._access_order:
            lru_entity = self._access_order.pop(0)
            if lru_entity in self._cache:
                del self._cache[lru_entity]
                logger.debug(f"Evicted LRU embedding: {lru_entity}")

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        current_mb = len(self._cache) * self.EMBEDDING_SIZE_BYTES / (1024 * 1024)

        return {
            "cached_embeddings": len(self._cache),
            "max_embeddings": self.max_cache_entries,
            "current_size_mb": current_mb,
            "max_size_mb": self.max_cache_mb,
            "utilization": len(self._cache) / self.max_cache_entries if self.max_cache_entries > 0 else 0,
            "loaded_areas": list(self._loaded_areas),
        }

    def clear(self):
        """Clear cache."""
        self._cache.clear()
        self._loaded_areas.clear()
        self._access_order.clear()
        logger.debug("Embedding cache cleared")

