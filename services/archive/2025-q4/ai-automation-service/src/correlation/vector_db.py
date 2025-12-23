"""
Correlation Vector Database

Epic 37, Story 37.1: Vector Database Foundation
Implements FAISS-based vector storage for O(n) similarity search (flat index).

Single-home NUC optimized (2025 patterns):
- Memory: ~30MB (flat index for single-home scale)
- Performance: Fast enough for <10k vectors on CPU
- Scale: Optimized for ~50-100 devices (~2,500-10,000 correlation pairs)
- Simple: No persistence, no removal - just add and search
"""

import logging
from typing import Optional, List, Tuple
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None

from shared.logging_config import get_logger

logger = get_logger(__name__)


class CorrelationVectorDatabase:
    """
    Vector database for correlation similarity search.
    
    Uses FAISS flat index (2025 best practice for single-home):
    - Flat index: Simple, fast for <10k vectors, CPU-only
    - L2 distance: Standard correlation distance metric
    - In-memory: No persistence needed (rebuild on restart)
    
    Single-home NUC optimization:
    - Flat index (not HNSW) - simple and sufficient
    - ~50-100 devices = ~2,500-10,000 correlation pairs
    - Memory: ~30MB for 10k vectors (32-dim float32)
    """
    
    def __init__(self, vector_dim: int = 32):
        """
        Initialize vector database.
        
        Args:
            vector_dim: Dimension of correlation feature vectors (default: 32)
        
        Raises:
            ImportError: If FAISS is not available
        """
        if not FAISS_AVAILABLE:
            raise ImportError(
                "FAISS not available. Install with: pip install faiss-cpu"
            )
        
        self.vector_dim = vector_dim
        
        # FAISS flat index (2025: simple, CPU-only, perfect for single-home)
        # Flat index: O(n) search, but fast enough for <10k vectors
        self.index = faiss.IndexFlatL2(vector_dim)
        
        # Metadata storage (entity pairs for each vector)
        self.vector_metadata: List[Tuple[str, str]] = []
        
        logger.info(
            "CorrelationVectorDatabase initialized (dim=%d, cpu-only)",
            vector_dim
        )
    
    def add_correlation_vector(
        self,
        entity1_id: str,
        entity2_id: str,
        feature_vector: np.ndarray
    ) -> None:
        """
        Add correlation feature vector to index.
        
        Args:
            entity1_id: Entity 1 ID
            entity2_id: Entity 2 ID
            feature_vector: Feature vector (shape: [vector_dim])
        
        Raises:
            ValueError: If vector dimension doesn't match
        """
        if feature_vector.shape[0] != self.vector_dim:
            raise ValueError(
                f"Vector dimension mismatch: expected {self.vector_dim}, "
                f"got {feature_vector.shape[0]}"
            )
        
        # Ensure vector is float32 and 2D (FAISS requirement)
        vector = feature_vector.astype(np.float32).reshape(1, -1)
        
        # Add to index
        self.index.add(vector)
        
        # Store metadata
        self.vector_metadata.append((entity1_id, entity2_id))
        
        logger.debug(
            "Added correlation vector: %s <-> %s (index size: %d)",
            entity1_id, entity2_id, self.index.ntotal
        )
    
    def search_similar_correlations(
        self,
        query_vector: np.ndarray,
        k: int = 10,
        min_similarity: Optional[float] = None
    ) -> List[Tuple[str, str, float]]:
        """
        Search for similar correlations using vector similarity.
        
        Args:
            query_vector: Query feature vector (shape: [vector_dim])
            k: Number of similar correlations to return
            min_similarity: Optional minimum similarity threshold (L2 distance)
        
        Returns:
            List of (entity1_id, entity2_id, distance) tuples
            (lower distance = more similar)
        
        Raises:
            ValueError: If vector dimension doesn't match or index is empty
        """
        if self.index.ntotal == 0:
            logger.warning("Vector database is empty, returning empty results")
            return []
        
        if query_vector.shape[0] != self.vector_dim:
            raise ValueError(
                f"Query vector dimension mismatch: expected {self.vector_dim}, "
                f"got {query_vector.shape[0]}"
            )
        
        # Ensure vector is float32 and 2D (FAISS requirement)
        query = query_vector.astype(np.float32).reshape(1, -1)
        
        # Search (O(n) with flat index - fast enough for single-home scale)
        # For <10k vectors, flat index is simple and sufficient
        distances, indices = self.index.search(query, min(k, self.index.ntotal))
        
        # Convert to results
        results = []
        for i, (idx, dist) in enumerate(zip(indices[0], distances[0])):
            if idx < 0:  # FAISS returns -1 for invalid indices
                continue
            
            if min_similarity is not None and dist > min_similarity:
                continue
            
            entity1_id, entity2_id = self.vector_metadata[idx]
            results.append((entity1_id, entity2_id, float(dist)))
        
        logger.debug(
            "Found %d similar correlations (query k=%d, min_similarity=%s)",
            len(results), k, min_similarity
        )
        
        return results
    
    
    def clear(self) -> None:
        """Clear all vectors from index."""
        self.index.reset()
        self.vector_metadata.clear()
        logger.info("Vector database cleared")
    
    def get_size(self) -> int:
        """Get number of vectors in index."""
        return self.index.ntotal
    
    def get_memory_usage_mb(self) -> float:
        """
        Get approximate memory usage in MB.
        
        Flat index memory: ~vector_dim * n_vectors * 4 bytes (float32)
        Plus metadata overhead.
        """
        vector_memory = self.vector_dim * self.index.ntotal * 4 / (1024 * 1024)
        metadata_memory = len(self.vector_metadata) * 64 / (1024 * 1024)  # Rough estimate
        return vector_memory + metadata_memory

