"""
Personalized Entity Index

Epic AI-12, Story AI12.1: Personalized Entity Index Builder
Builds and maintains a personalized searchable index of user's actual Home Assistant devices
with all name variations (name, name_by_user, aliases, friendly_name) and semantic embeddings.

Single-home NUC optimized:
- In-memory index with SQLite persistence (optional)
- Semantic embeddings for all name variations
- Fast lookup (<100ms per query)
- Memory efficient (<50MB for 100 devices)
"""

import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

from .embedding_cache import EmbeddingCache
from .query_cache import QueryCache

logger = logging.getLogger(__name__)


@dataclass
class EntityVariant:
    """Represents a single name variant for an entity"""
    entity_id: str
    variant_name: str
    variant_type: str  # 'name', 'name_by_user', 'alias', 'friendly_name'
    embedding: Optional[list[float]] = None
    area_id: Optional[str] = None
    area_name: Optional[str] = None


@dataclass
class EntityIndexEntry:
    """Represents a complete entity with all variants"""
    entity_id: str
    domain: str
    device_id: Optional[str] = None
    area_id: Optional[str] = None
    area_name: Optional[str] = None
    variants: list[EntityVariant] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


class PersonalizedEntityIndex:
    """
    Personalized entity index for user's actual Home Assistant devices.
    
    Features:
    - Indexes all name variations per entity
    - Semantic embeddings for natural language matching
    - Area-aware indexing
    - Fast lookup (<100ms)
    - Memory efficient (<50MB for 100 devices)
    """
    
    def __init__(
        self,
        embedding_model: Optional[str] = None,
        enable_persistence: bool = False,
        persistence_path: Optional[str] = None,
        embedding_cache: Optional[EmbeddingCache] = None,
        query_cache: Optional[QueryCache] = None
    ):
        """
        Initialize personalized entity index.
        
        Args:
            embedding_model: Sentence transformer model name (default: 'all-MiniLM-L6-v2')
            enable_persistence: Enable SQLite persistence (optional)
            persistence_path: Path to SQLite database (if persistence enabled)
            embedding_cache: Optional EmbeddingCache instance (creates default if None)
            query_cache: Optional QueryCache instance (creates default if None)
        """
        self.embedding_model_name = embedding_model or "all-MiniLM-L6-v2"
        self.enable_persistence = enable_persistence
        self.persistence_path = persistence_path
        
        # In-memory index: entity_id -> EntityIndexEntry
        self._index: dict[str, EntityIndexEntry] = {}
        
        # Reverse index: variant_name -> list[entity_id] (for fast lookup)
        self._variant_index: dict[str, list[str]] = defaultdict(list)
        
        # Area index: area_id -> list[entity_id]
        self._area_index: dict[str, list[str]] = defaultdict(list)
        
        # Embedding model (lazy load)
        self._embedding_model: Optional[Any] = None
        
        # Caching (Epic AI-12 Story AI12.10)
        self._embedding_cache = embedding_cache or EmbeddingCache(max_size=1000)
        self._query_cache = query_cache or QueryCache(max_size=500, ttl_seconds=300)
        
        # Statistics
        self._stats = {
            "total_entities": 0,
            "total_variants": 0,
            "total_areas": 0,
            "last_build_time": None,
            "build_duration_ms": None
        }
        
        logger.info(f"PersonalizedEntityIndex initialized (model={self.embedding_model_name}, caching enabled)")
    
    def _get_embedding_model(self) -> Any:
        """Get or load embedding model (lazy loading)"""
        if self._embedding_model is None:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                logger.warning("sentence-transformers not available, embeddings disabled")
                return None
            
            try:
                logger.info(f"Loading embedding model: {self.embedding_model_name}")
                self._embedding_model = SentenceTransformer(self.embedding_model_name)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}", exc_info=True)
                return None
        
        return self._embedding_model
    
    def _generate_embedding(self, text: str) -> Optional[list[float]]:
        """
        Generate semantic embedding for text (with caching).
        
        Epic AI-12 Story AI12.10: Uses EmbeddingCache to avoid regenerating embeddings.
        """
        if not text or not text.strip():
            return None
        
        # Check cache first
        cached_embedding = self._embedding_cache.get(text)
        if cached_embedding is not None:
            return cached_embedding
        
        # Generate embedding
        model = self._get_embedding_model()
        if model is None:
            return None
        
        try:
            embedding = model.encode(text, convert_to_numpy=True)
            embedding_list = embedding.tolist()
            
            # Cache the embedding
            self._embedding_cache.put(text, embedding_list)
            
            return embedding_list
        except Exception as e:
            logger.warning(f"Failed to generate embedding for '{text}': {e}")
            return None
    
    def add_entity(
        self,
        entity_id: str,
        domain: str,
        name_variants: dict[str, str],  # variant_type -> name
        device_id: Optional[str] = None,
        area_id: Optional[str] = None,
        area_name: Optional[str] = None
    ) -> None:
        """
        Add entity to index with all name variants.
        
        Args:
            entity_id: Entity ID (e.g., 'light.office_lamp')
            domain: Entity domain (e.g., 'light')
            name_variants: Dictionary of variant_type -> name
                Example: {'name': 'Office Lamp', 'name_by_user': 'Desk Light', 'aliases': ['Lamp', 'Light']}
            device_id: Optional device ID
            area_id: Optional area ID
            area_name: Optional area name
        """
        # Create entity entry
        entry = EntityIndexEntry(
            entity_id=entity_id,
            domain=domain,
            device_id=device_id,
            area_id=area_id,
            area_name=area_name,
            last_updated=datetime.now()
        )
        
        # Create variants with embeddings
        for variant_type, variant_name in name_variants.items():
            if not variant_name or not variant_name.strip():
                continue
            
            # Generate embedding
            embedding = self._generate_embedding(variant_name)
            
            variant = EntityVariant(
                entity_id=entity_id,
                variant_name=variant_name.strip(),
                variant_type=variant_type,
                embedding=embedding,
                area_id=area_id,
                area_name=area_name
            )
            
            entry.variants.append(variant)
            
            # Add to reverse index
            self._variant_index[variant_name.strip().lower()].append(entity_id)
        
        # Add to index
        self._index[entity_id] = entry
        
        # Add to area index
        if area_id:
            self._area_index[area_id].append(entity_id)
    
    def get_entity(self, entity_id: str) -> Optional[EntityIndexEntry]:
        """Get entity entry by entity_id"""
        return self._index.get(entity_id)
    
    def search_by_name(
        self,
        query: str,
        domain: Optional[str] = None,
        area_id: Optional[str] = None,
        limit: int = 10
    ) -> list[tuple[str, float]]:
        """
        Search entities by name using semantic similarity (with query caching).
        
        Epic AI-12 Story AI12.10: Uses QueryCache to avoid recalculating similarity scores.
        
        Args:
            query: Search query
            domain: Optional domain filter
            area_id: Optional area filter
            limit: Maximum results to return
        
        Returns:
            List of (entity_id, similarity_score) tuples, sorted by score
        """
        if not query or not query.strip():
            return []
        
        # Check query cache first
        cached_results = self._query_cache.get(query, domain, area_id, limit)
        if cached_results is not None:
            return cached_results
        
        query_embedding = self._generate_embedding(query.strip())
        if query_embedding is None:
            # Fallback to exact/fuzzy matching if embeddings unavailable
            results = self._search_by_exact_match(query, domain, area_id, limit)
            # Cache the results
            self._query_cache.put(query, results, domain, area_id, limit)
            return results
        
        # Calculate similarity scores
        results: list[tuple[str, float]] = []
        
        for entity_id, entry in self._index.items():
            # Apply filters
            if domain and entry.domain != domain:
                continue
            if area_id and entry.area_id != area_id:
                continue
            
            # Find best matching variant
            best_score = 0.0
            for variant in entry.variants:
                if variant.embedding is None:
                    continue
                
                # Cosine similarity
                similarity = self._cosine_similarity(query_embedding, variant.embedding)
                best_score = max(best_score, similarity)
            
            if best_score > 0:
                results.append((entity_id, best_score))
        
        # Sort by score (descending) and limit
        results.sort(key=lambda x: x[1], reverse=True)
        final_results = results[:limit]
        
        # Cache the results
        self._query_cache.put(query, final_results, domain, area_id, limit)
        
        return final_results
    
    def _search_by_exact_match(
        self,
        query: str,
        domain: Optional[str] = None,
        area_id: Optional[str] = None,
        limit: int = 10
    ) -> list[tuple[str, float]]:
        """Fallback search using exact/fuzzy matching when embeddings unavailable"""
        query_lower = query.strip().lower()
        results: list[tuple[str, float]] = []
        
        # Exact match
        if query_lower in self._variant_index:
            for entity_id in self._variant_index[query_lower]:
                entry = self._index.get(entity_id)
                if entry:
                    if domain and entry.domain != domain:
                        continue
                    if area_id and entry.area_id != area_id:
                        continue
                    results.append((entity_id, 1.0))
        
        # Partial match
        for variant_name, entity_ids in self._variant_index.items():
            if query_lower in variant_name or variant_name in query_lower:
                for entity_id in entity_ids:
                    if entity_id not in [r[0] for r in results]:
                        entry = self._index.get(entity_id)
                        if entry:
                            if domain and entry.domain != domain:
                                continue
                            if area_id and entry.area_id != area_id:
                                continue
                            score = len(query_lower) / len(variant_name) if variant_name else 0.5
                            results.append((entity_id, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import numpy as np
            vec1_np = np.array(vec1)
            vec2_np = np.array(vec2)
            dot_product = np.dot(vec1_np, vec2_np)
            norm1 = np.linalg.norm(vec1_np)
            norm2 = np.linalg.norm(vec2_np)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            logger.warning(f"Failed to calculate cosine similarity: {e}")
            return 0.0
    
    def get_entities_by_area(self, area_id: str) -> list[str]:
        """Get all entity IDs in a specific area"""
        return self._area_index.get(area_id, []).copy()
    
    def get_stats(self) -> dict[str, Any]:
        """Get index statistics (including cache statistics)"""
        self._stats["total_entities"] = len(self._index)
        self._stats["total_variants"] = sum(len(entry.variants) for entry in self._index.values())
        self._stats["total_areas"] = len(self._area_index)
        
        # Include cache statistics (Epic AI-12 Story AI12.10)
        stats = self._stats.copy()
        stats["embedding_cache"] = self._embedding_cache.get_stats()
        stats["query_cache"] = self._query_cache.get_stats()
        
        return stats
    
    def clear(self) -> None:
        """Clear all entries from index"""
        self._index.clear()
        self._variant_index.clear()
        self._area_index.clear()
        self._stats = {
            "total_entities": 0,
            "total_variants": 0,
            "total_areas": 0,
            "last_build_time": None,
            "build_duration_ms": None
        }
        logger.info("Index cleared")

