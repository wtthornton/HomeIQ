"""
RAG Service

Core service for semantic knowledge storage and retrieval.
Following 2025 patterns: async/await, dependency injection, type hints.
"""

import logging
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.openvino_client import EmbeddingGenerationError, OpenVINOClient
from ..database.models import RAGKnowledge

logger = logging.getLogger(__name__)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        a: First vector (numpy array)
        b: Second vector (numpy array)
    
    Returns:
        Cosine similarity score (0.0-1.0)
    """
    a_norm = a / (np.linalg.norm(a) + 1e-8)
    b_norm = b / (np.linalg.norm(b) + 1e-8)
    return float(np.dot(a_norm, b_norm))


class RAGService:
    """
    Service for semantic knowledge storage and retrieval.
    
    Features:
    - Store text with embeddings
    - Retrieve similar knowledge using semantic similarity
    - Search with filters
    - Update success scores
    - Embedding cache for performance
    """

    def __init__(
        self,
        db: AsyncSession,
        openvino_client: OpenVINOClient,
        embedding_cache: dict[str, Any] | None = None,
        embedding_cache_size: int = 100
    ):
        """
        Initialize RAG service.

        Args:
            db: Database session
            openvino_client: OpenVINO client for embeddings
            embedding_cache: Shared embedding cache dict (singleton, persists across requests)
            embedding_cache_size: Size of in-memory embedding cache (default: 100)
        """
        self.db = db
        self.openvino_client = openvino_client
        self._embedding_cache: dict[str, Any] = embedding_cache if embedding_cache is not None else {}
        self._cache_size = embedding_cache_size

    async def _get_embedding(self, text: str) -> tuple[np.ndarray, bool]:
        """
        Get embedding for text (with cache).
        
        Args:
            text: Text to embed
        
        Returns:
            Tuple of (embedding vector, cache_hit bool)
            - embedding: 1024-dim numpy array
            - cache_hit: True if embedding was from cache, False if newly generated
        
        Raises:
            EmbeddingGenerationError: If embedding generation fails
        """
        # Check cache first
        if text in self._embedding_cache:
            logger.debug(f"Cache hit for embedding: {text[:50]}...")
            return self._embedding_cache[text], True

        try:
            # Get embedding from OpenVINO service
            embeddings = await self.openvino_client.get_embeddings([text], normalize=True)
            if not embeddings:
                raise EmbeddingGenerationError("No embeddings returned from OpenVINO service")
            
            embedding = np.array(embeddings[0])

            # Cache embedding (simple LRU: remove oldest if cache full)
            if len(self._embedding_cache) >= self._cache_size:
                # Remove first (oldest) entry
                oldest_key = next(iter(self._embedding_cache))
                del self._embedding_cache[oldest_key]

            self._embedding_cache[text] = embedding
            logger.debug(f"Generated and cached embedding for: {text[:50]}...")
            return embedding, False

        except EmbeddingGenerationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}")
            raise EmbeddingGenerationError(f"Failed to generate embedding: {e}") from e

    async def store(
        self,
        text: str,
        knowledge_type: str,
        metadata: dict[str, Any] | None = None,
        success_score: float = 0.5
    ) -> tuple[int, bool]:
        """
        Store text with semantic embedding.
        
        Args:
            text: Text to store
            knowledge_type: Type ('query', 'pattern', 'blueprint', 'automation', etc.)
            metadata: Additional metadata (optional)
            success_score: Success score (0.0-1.0, default: 0.5)
        
        Returns:
            Tuple of (entry ID, cache_hit bool)
            - entry ID: ID of stored entry
            - cache_hit: True if embedding was from cache, False if newly generated
        
        Raises:
            EmbeddingGenerationError: If embedding generation fails
        """
        try:
            # Generate embedding
            embedding, cache_hit = await self._get_embedding(text)

            # Store in database
            entry = RAGKnowledge(
                text=text,
                embedding=embedding.tolist(),  # Convert to list for JSON storage
                knowledge_type=knowledge_type,
                metadata_json=metadata or {},  # Use metadata_json attribute
                success_score=success_score
            )

            self.db.add(entry)
            await self.db.commit()
            await self.db.refresh(entry)

            logger.info(f"Stored RAG knowledge: type={knowledge_type}, id={entry.id}, text='{text[:50]}...'")
            return entry.id, cache_hit

        except EmbeddingGenerationError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error storing RAG knowledge: {e}")
            raise

    async def retrieve(
        self,
        query: str,
        knowledge_type: str | None = None,
        top_k: int = 5,
        min_similarity: float = 0.7
    ) -> tuple[list[dict[str, Any]], bool]:
        """
        Retrieve similar entries using semantic similarity.
        
        Args:
            query: Query text
            knowledge_type: Filter by type (optional)
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0.0-1.0)
        
        Returns:
            Tuple of (results list, cache_hit bool)
            - results: List of similar entries with similarity scores, sorted by similarity (descending)
              Each entry contains: id, text, similarity, knowledge_type, metadata, success_score
            - cache_hit: True if query embedding was from cache, False if newly generated
        
        Raises:
            EmbeddingGenerationError: If embedding generation fails
        """
        try:
            # Generate query embedding
            query_embedding, cache_hit = await self._get_embedding(query)

            # Query database
            stmt = select(RAGKnowledge)
            if knowledge_type:
                stmt = stmt.where(RAGKnowledge.knowledge_type == knowledge_type)

            result = await self.db.execute(stmt)
            entries = result.scalars().all()

            # Calculate similarities
            results = []
            for entry in entries:
                entry_embedding = np.array(entry.embedding)
                similarity = cosine_similarity(query_embedding, entry_embedding)
                
                if similarity >= min_similarity:
                    results.append({
                        'id': entry.id,
                        'text': entry.text,
                        'similarity': similarity,
                        'knowledge_type': entry.knowledge_type,
                        'metadata': entry.metadata_json,  # Use metadata_json attribute, expose as 'metadata' in response
                        'success_score': entry.success_score,
                        'created_at': entry.created_at.isoformat() if entry.created_at else None,
                    })

            # Sort by similarity (descending) and take top_k
            results.sort(key=lambda x: x['similarity'], reverse=True)
            results = results[:top_k]

            logger.debug(f"Retrieved {len(results)} similar entries for query: {query[:50]}...")
            return results, cache_hit

        except EmbeddingGenerationError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving RAG knowledge: {e}")
            raise

    async def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
        min_similarity: float = 0.7
    ) -> tuple[list[dict[str, Any]], bool]:
        """
        Search with optional filters (alias for retrieve with filters).
        
        Args:
            query: Query text
            filters: Optional filters (knowledge_type, metadata keys, etc.)
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0.0-1.0)
        
        Returns:
            Tuple of (results list, cache_hit bool)
            - results: List of similar entries with similarity scores
            - cache_hit: True if query embedding was from cache, False if newly generated
        """
        knowledge_type = filters.get('knowledge_type') if filters else None
        return await self.retrieve(query, knowledge_type, top_k, min_similarity)

    async def update_success_score(self, id: int, score: float) -> None:
        """
        Update success score for an entry.
        
        Args:
            id: Entry ID
            score: New success score (0.0-1.0)
        
        Raises:
            ValueError: If entry not found
        """
        try:
            result = await self.db.get(RAGKnowledge, id)
            if not result:
                raise ValueError(f"RAG knowledge entry not found: id={id}")
            
            result.success_score = score
            await self.db.commit()
            await self.db.refresh(result)
            
            logger.info(f"Updated success score for entry {id}: {score}")
        except ValueError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating success score: {e}")
            raise
