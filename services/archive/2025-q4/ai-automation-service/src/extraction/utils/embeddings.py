"""
Embedding Utilities (2025)

Centralized handling for sentence-transformers models and vector similarity.
"""

import logging
import numpy as np
from typing import List, Union, Optional

logger = logging.getLogger(__name__)

# Global singleton for the model
_EMBEDDING_MODEL = None
_SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("sentence-transformers not available, embedding features disabled")

class EmbeddingService:
    """
    Service for generating text embeddings and calculating similarity.
    Uses singleton model instance for performance.
    """
    
    MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
    
    @classmethod
    def get_model(cls):
        """Lazy load the model."""
        global _EMBEDDING_MODEL
        
        if not _SENTENCE_TRANSFORMERS_AVAILABLE:
            return None
            
        if _EMBEDDING_MODEL is None:
            try:
                logger.info(f"Loading embedding model: {cls.MODEL_NAME}")
                _EMBEDDING_MODEL = SentenceTransformer(cls.MODEL_NAME)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                _EMBEDDING_MODEL = None
                
        return _EMBEDDING_MODEL

    @classmethod
    def encode(cls, texts: Union[str, List[str]]) -> Optional[np.ndarray]:
        """Generate embeddings for text(s)."""
        model = cls.get_model()
        if not model:
            return None
            
        try:
            # encode returns numpy array by default in newer versions, or list
            embeddings = model.encode(texts, convert_to_numpy=True)
            return embeddings
        except Exception as e:
            logger.error(f"Encoding failed: {e}")
            return None

    @classmethod
    def cosine_similarity(cls, query_embedding: np.ndarray, candidate_embeddings: np.ndarray) -> np.ndarray:
        """
        Calculate cosine similarity between a query and multiple candidates.
        
        Args:
            query_embedding: Shape (dim,)
            candidate_embeddings: Shape (n, dim)
            
        Returns:
            Array of similarity scores (n,)
        """
        if query_embedding is None or candidate_embeddings is None:
            return np.array([])
            
        # Ensure query is 1D or 2D match
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)
            
        # Normalize vectors
        norm_query = np.linalg.norm(query_embedding, axis=1, keepdims=True)
        norm_candidates = np.linalg.norm(candidate_embeddings, axis=1, keepdims=True)
        
        # Avoid division by zero
        norm_query[norm_query == 0] = 1e-10
        norm_candidates[norm_candidates == 0] = 1e-10
        
        # Calculate similarity
        # (1, dim) @ (dim, n) -> (1, n)
        dot_product = np.dot(query_embedding, candidate_embeddings.T)
        similarity = dot_product / (norm_query * norm_candidates.T)
        
        return similarity.flatten()

