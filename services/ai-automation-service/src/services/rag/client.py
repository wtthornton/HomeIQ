"""
Generic RAG Client for semantic knowledge storage and retrieval.

Uses OpenVINO service for embeddings and SQLite for storage.
Implements cosine similarity for semantic search.
Now includes hybrid retrieval (dense + sparse) with cross-encoder reranking.
"""

import logging
from datetime import datetime
from typing import Any

import httpx
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import SemanticKnowledge
from .bm25_retrieval import BM25Retriever
from .cross_encoder_reranker import CrossEncoderReranker
from .exceptions import EmbeddingGenerationError, RetrievalError, StorageError
from .query_expansion import QueryExpander

logger = logging.getLogger(__name__)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        a: First vector (1D numpy array)
        b: Second vector (1D numpy array)
        
    Returns:
        Cosine similarity score (0.0-1.0)
    """
    # Normalize vectors (should already be normalized from OpenVINO, but ensure)
    a_norm = a / (np.linalg.norm(a) + 1e-8)
    b_norm = b / (np.linalg.norm(b) + 1e-8)
    return float(np.dot(a_norm, b_norm))


class RAGClient:
    """
    Generic RAG client for semantic knowledge retrieval.
    
    Can be used for:
    - Query clarification (primary use case)
    - Pattern matching
    - Suggestion generation
    - Device intelligence
    - Automation mining
    """

    def __init__(
        self,
        openvino_service_url: str,
        db_session: AsyncSession,
        embedding_cache_size: int = 100,
        enable_hybrid_retrieval: bool = True,
        enable_reranking: bool = True
    ):
        """
        Initialize RAG client.
        
        Args:
            openvino_service_url: URL of OpenVINO service (e.g., "http://openvino-service:8019")
            db_session: Async database session
            embedding_cache_size: Size of in-memory embedding cache (default: 100)
            enable_hybrid_retrieval: Enable hybrid retrieval (dense + sparse BM25) (default: True)
            enable_reranking: Enable cross-encoder reranking (default: True)
        """
        self.openvino_url = openvino_service_url.rstrip('/')
        self.db = db_session
        self._embedding_cache: dict[str, np.ndarray] = {}
        self._cache_size = embedding_cache_size
        self._client = httpx.AsyncClient(timeout=10.0)

        # Initialize 2025 best practices components
        self.enable_hybrid_retrieval = enable_hybrid_retrieval
        self.enable_reranking = enable_reranking
        self.query_expander = QueryExpander()
        self.bm25_retriever = BM25Retriever() if enable_hybrid_retrieval else None
        self.cross_encoder_reranker = CrossEncoderReranker() if enable_reranking else None

        # Cache for BM25 index (built on first retrieval)
        self._bm25_indexed = False

        logger.info(
            f"RAGClient initialized with OpenVINO service: {self.openvino_url} "
            f"(hybrid={enable_hybrid_retrieval}, reranking={enable_reranking})"
        )

    async def _get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding from OpenVINO service (with cache).
        
        Args:
            text: Text to embed
            
        Returns:
            384-dim numpy array
            
        Raises:
            EmbeddingGenerationError: If embedding generation fails
        """
        # Check cache first
        if text in self._embedding_cache:
            logger.debug(f"Cache hit for embedding: {text[:50]}...")
            return self._embedding_cache[text]

        try:
            response = await self._client.post(
                f"{self.openvino_url}/embeddings",
                json={
                    "texts": [text],
                    "normalize": True  # Normalize for cosine similarity
                },
                timeout=5.0
            )
            response.raise_for_status()

            data = response.json()
            embedding = np.array(data["embeddings"][0])

            # Cache embedding (simple LRU: remove oldest if cache full)
            if len(self._embedding_cache) >= self._cache_size:
                # Remove first (oldest) entry
                oldest_key = next(iter(self._embedding_cache))
                del self._embedding_cache[oldest_key]

            self._embedding_cache[text] = embedding
            logger.debug(f"Generated and cached embedding for: {text[:50]}...")
            return embedding

        except httpx.HTTPError as e:
            logger.error(f"HTTP error generating embedding: {e}")
            raise EmbeddingGenerationError(f"Failed to generate embedding: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}")
            raise EmbeddingGenerationError(f"Failed to generate embedding: {e}") from e

    async def store(
        self,
        text: str,
        knowledge_type: str,
        metadata: dict[str, Any] | None = None,
        success_score: float = 0.5
    ) -> int:
        """
        Store text with semantic embedding.
        
        Args:
            text: Text to store
            knowledge_type: Type ('query', 'pattern', 'blueprint', 'automation', etc.)
            metadata: Additional metadata (optional)
            success_score: Success score (0.0-1.0, default: 0.5)
            
        Returns:
            ID of stored entry
            
        Raises:
            StorageError: If storage fails
        """
        try:
            # Generate embedding
            embedding = await self._get_embedding(text)

            # Store in database
            entry = SemanticKnowledge(
                text=text,
                embedding=embedding.tolist(),  # Convert to list for JSON storage
                knowledge_type=knowledge_type,
                knowledge_metadata=metadata or {},  # Renamed from 'metadata' to avoid SQLAlchemy reserved word conflict
                success_score=success_score
            )

            self.db.add(entry)
            await self.db.commit()
            await self.db.refresh(entry)

            logger.info(f"Stored semantic knowledge: type={knowledge_type}, id={entry.id}, text='{text[:50]}...'")
            return entry.id

        except EmbeddingGenerationError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error storing semantic knowledge: {e}")
            raise StorageError(f"Failed to store semantic knowledge: {e}") from e

    async def retrieve(
        self,
        query: str,
        knowledge_type: str | None = None,
        top_k: int = 5,
        min_similarity: float = 0.7,
        filter_metadata: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Retrieve similar entries using semantic similarity.
        
        Args:
            query: Query text
            knowledge_type: Filter by type (optional)
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0.0-1.0)
            filter_metadata: Filter by metadata (optional, supports nested dict matching)
            
        Returns:
            List of similar entries with similarity scores, sorted by similarity (descending)
            Each entry contains: id, text, similarity, knowledge_type, metadata, success_score
            
        Raises:
            RetrievalError: If retrieval fails
        """
        try:
            # Generate query embedding
            query_embedding = await self._get_embedding(query)

            # Query database
            stmt = select(SemanticKnowledge)
            if knowledge_type:
                stmt = stmt.where(SemanticKnowledge.knowledge_type == knowledge_type)

            result = await self.db.execute(stmt)
            entries = result.scalars().all()

            if not entries:
                logger.debug(f"No entries found for knowledge_type={knowledge_type}")
                return []

            # Calculate cosine similarity for each entry
            similarities = []
            for entry in entries:
                entry_embedding = np.array(entry.embedding)
                similarity = cosine_similarity(query_embedding, entry_embedding)

                # Apply filters
                if similarity < min_similarity:
                    continue

                if filter_metadata:
                    if not self._matches_metadata(entry.knowledge_metadata or {}, filter_metadata):
                        continue

                similarities.append({
                    'id': entry.id,
                    'text': entry.text,
                    'similarity': float(similarity),
                    'knowledge_type': entry.knowledge_type,
                    'metadata': entry.knowledge_metadata or {},  # Map to 'metadata' in response for API compatibility
                    'success_score': entry.success_score,
                    'created_at': entry.created_at.isoformat() if entry.created_at else None
                })

            # Sort by similarity (descending) and return top_k
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            results = similarities[:top_k]

            logger.debug(f"Retrieved {len(results)} similar entries for query: {query[:50]}...")
            return results

        except EmbeddingGenerationError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving semantic knowledge: {e}")
            raise RetrievalError(f"Failed to retrieve semantic knowledge: {e}") from e

    async def retrieve_hybrid(
        self,
        query: str,
        knowledge_type: str | None = None,
        top_k: int = 5,
        min_similarity: float = 0.7,
        filter_metadata: dict[str, Any] | None = None,
        use_query_expansion: bool = True,
        use_reranking: bool = True,
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4
    ) -> list[dict[str, Any]]:
        """
        Hybrid retrieval using dense (embeddings) + sparse (BM25) + reranking.
        
        Implements 2025 best practices:
        1. Query expansion (synonyms, related terms)
        2. Hybrid retrieval (dense + sparse BM25)
        3. Cross-encoder reranking (final ranking)
        
        Args:
            query: Query text
            knowledge_type: Filter by type (optional)
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0.0-1.0)
            filter_metadata: Filter by metadata (optional)
            use_query_expansion: Enable query expansion (default: True)
            use_reranking: Enable cross-encoder reranking (default: True)
            dense_weight: Weight for dense retrieval (default: 0.6)
            sparse_weight: Weight for sparse retrieval (default: 0.4)
            
        Returns:
            List of similar entries with hybrid scores, sorted by relevance
        """
        try:
            # Step 1: Query expansion
            expanded_query = query
            if use_query_expansion:
                expanded_query = self.query_expander.expand(query)
                logger.debug(f"Query expansion: '{query}' → '{expanded_query}'")

            # Step 2: Dense retrieval (embeddings)
            dense_results = await self.retrieve(
                query=expanded_query,
                knowledge_type=knowledge_type,
                top_k=top_k * 3,  # Get more candidates for hybrid combination
                min_similarity=min_similarity,
                filter_metadata=filter_metadata
            )

            if not dense_results:
                logger.debug("No dense results found")
                return []

            # Step 3: Sparse retrieval (BM25) if enabled
            if self.enable_hybrid_retrieval and self.bm25_retriever:
                # Build BM25 index if not already built
                if not self._bm25_indexed:
                    # Get all entries for indexing
                    stmt = select(SemanticKnowledge)
                    if knowledge_type:
                        stmt = stmt.where(SemanticKnowledge.knowledge_type == knowledge_type)

                    result = await self.db.execute(stmt)
                    all_entries = result.scalars().all()

                    # Convert to documents for BM25
                    documents = []
                    for entry in all_entries:
                        doc = {
                            'id': entry.id,
                            'text': entry.text,
                            'knowledge_type': entry.knowledge_type,
                            'metadata': entry.knowledge_metadata or {},
                            'success_score': entry.success_score
                        }
                        documents.append(doc)

                    # Index documents
                    self.bm25_retriever.index(documents, text_field='text')
                    self._bm25_indexed = True
                    logger.debug(f"Built BM25 index with {len(documents)} documents")

                # Hybrid search: combine dense + sparse
                hybrid_results = self.bm25_retriever.search_hybrid(
                    query=expanded_query,
                    dense_results=dense_results,
                    top_k=top_k * 2,  # More candidates before reranking
                    dense_weight=dense_weight,
                    sparse_weight=sparse_weight,
                    text_field='text'
                )

                results = hybrid_results
            else:
                results = dense_results

            # Step 4: Cross-encoder reranking if enabled
            if use_reranking and self.enable_reranking and self.cross_encoder_reranker:
                results = self.cross_encoder_reranker.rerank_with_hybrid_score(
                    query=expanded_query,
                    candidates=results,
                    top_k=top_k,
                    text_field='text',
                    cross_encoder_weight=0.7,
                    original_score_weight=0.3
                )
            else:
                # Just take top_k if no reranking
                results = results[:top_k]

            logger.info(
                f"Hybrid retrieval: '{query[:50]}...' → {len(results)} results "
                f"(expansion={use_query_expansion}, reranking={use_reranking})"
            )

            return results

        except Exception as e:
            logger.error(f"Error in hybrid retrieval: {e}")
            # Fallback to standard retrieval
            logger.warning("Falling back to standard dense retrieval")
            return await self.retrieve(
                query=query,
                knowledge_type=knowledge_type,
                top_k=top_k,
                min_similarity=min_similarity,
                filter_metadata=filter_metadata
            )

    def _matches_metadata(self, entry_metadata: dict[str, Any], filter_metadata: dict[str, Any]) -> bool:
        """
        Check if entry metadata matches filter criteria.
        
        Supports:
        - Exact value matching: {"status": "deployed"}
        - Nested dict matching: {"device": {"type": "light"}}
        - Comparison operators: {"confidence": {">": 0.8}}
        
        Args:
            entry_metadata: Entry metadata
            filter_metadata: Filter criteria
            
        Returns:
            True if metadata matches filter
        """
        for key, filter_value in filter_metadata.items():
            entry_value = entry_metadata.get(key)

            if entry_value is None:
                return False

            # Handle comparison operators
            if isinstance(filter_value, dict):
                for op, op_value in filter_value.items():
                    if op == ">":
                        if not (isinstance(entry_value, (int, float)) and entry_value > op_value):
                            return False
                    elif op == ">=":
                        if not (isinstance(entry_value, (int, float)) and entry_value >= op_value):
                            return False
                    elif op == "<":
                        if not (isinstance(entry_value, (int, float)) and entry_value < op_value):
                            return False
                    elif op == "<=":
                        if not (isinstance(entry_value, (int, float)) and entry_value <= op_value):
                            return False
                    elif op == "==":
                        if entry_value != op_value:
                            return False
                    elif op == "!=":
                        if entry_value == op_value:
                            return False
                    else:
                        # Nested dict matching
                        if not isinstance(entry_value, dict):
                            return False
                        if not self._matches_metadata(entry_value, {op: op_value}):
                            return False
            else:
                # Exact value matching
                if entry_value != filter_value:
                    return False

        return True

    async def update_success_score(
        self,
        entry_id: int,
        success_score: float
    ) -> None:
        """
        Update success score for an entry (for learning from user feedback).
        
        Args:
            entry_id: ID of entry to update
            success_score: New success score (0.0-1.0)
            
        Raises:
            StorageError: If update fails
        """
        try:
            result = await self.db.execute(
                select(SemanticKnowledge).where(SemanticKnowledge.id == entry_id)
            )
            entry = result.scalar_one_or_none()

            if not entry:
                raise StorageError(f"Entry with id={entry_id} not found")

            entry.success_score = max(0.0, min(1.0, success_score))  # Clamp to [0.0, 1.0]
            entry.updated_at = datetime.utcnow()

            await self.db.commit()
            logger.info(f"Updated success score for entry {entry_id}: {success_score}")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating success score: {e}")
            raise StorageError(f"Failed to update success score: {e}") from e

    async def close(self):
        """Close HTTP client (call when done with client)"""
        await self._client.aclose()
        logger.debug("RAGClient HTTP client closed")

