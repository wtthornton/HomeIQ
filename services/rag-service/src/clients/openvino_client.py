"""
OpenVINO Service Client

Async HTTP client for OpenVINO service (embeddings, reranking).
Following 2025 patterns: httpx.AsyncClient with retry logic.
"""

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import settings

logger = logging.getLogger(__name__)


class OpenVINOClientError(Exception):
    """Base exception for OpenVINO client errors."""
    pass


class EmbeddingGenerationError(OpenVINOClientError):
    """Exception raised when embedding generation fails."""
    pass


class RerankingError(OpenVINOClientError):
    """Exception raised when reranking fails."""
    pass


class OpenVINOClient:
    """
    Async client for OpenVINO service.
    
    Features:
    - Async HTTP requests with httpx
    - Automatic retry logic
    - Proper error handling
    - Type hints throughout
    """

    def __init__(self, base_url: str | None = None):
        """
        Initialize OpenVINO client.
        
        Args:
            base_url: Base URL for OpenVINO service (defaults to settings.openvino_service_url)
        """
        self.base_url = (base_url or settings.openvino_service_url).rstrip('/')
        
        # Create async HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10
            ),
        )
        
        logger.info(f"OpenVINO client initialized with base_url={self.base_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def get_embeddings(
        self,
        texts: list[str],
        normalize: bool = True
    ) -> list[list[float]]:
        """
        Get embeddings for texts from OpenVINO service.
        
        Args:
            texts: List of texts to embed
            normalize: Whether to normalize embeddings (default: True)
        
        Returns:
            List of embedding vectors (1024-dim each)
        
        Raises:
            EmbeddingGenerationError: If embedding generation fails
        """
        if not texts:
            return []
        
        try:
            response = await self.client.post(
                f"{self.base_url}/embeddings",
                json={
                    "texts": texts,
                    "normalize": normalize
                },
                timeout=30.0
            )
            response.raise_for_status()
            
            data = response.json()
            embeddings = data.get("embeddings", [])
            
            logger.debug(f"Generated embeddings for {len(texts)} texts")
            return embeddings
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error generating embeddings: {e.response.status_code} - {e.response.text}")
            raise EmbeddingGenerationError(f"Failed to generate embeddings: {e}") from e
        except httpx.HTTPError as e:
            logger.error(f"HTTP error generating embeddings: {e}")
            raise EmbeddingGenerationError(f"Failed to generate embeddings: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error generating embeddings: {e}")
            raise EmbeddingGenerationError(f"Failed to generate embeddings: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int = 10
    ) -> list[dict[str, Any]]:
        """
        Rerank candidates using OpenVINO reranker model.
        
        Args:
            query: Query text
            candidates: List of candidate dictionaries (must have 'text' key)
            top_k: Number of top results to return
        
        Returns:
            List of reranked candidates (dictionaries with scores)
        
        Raises:
            RerankingError: If reranking fails
        """
        if not candidates:
            return []
        
        try:
            response = await self.client.post(
                f"{self.base_url}/rerank",
                json={
                    "query": query,
                    "candidates": candidates,
                    "top_k": top_k
                },
                timeout=30.0
            )
            response.raise_for_status()
            
            data = response.json()
            ranked_candidates = data.get("ranked_candidates", [])
            
            logger.debug(f"Reranked {len(candidates)} candidates, returning top {top_k}")
            return ranked_candidates
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error reranking: {e.response.status_code} - {e.response.text}")
            raise RerankingError(f"Failed to rerank: {e}") from e
        except httpx.HTTPError as e:
            logger.error(f"HTTP error reranking: {e}")
            raise RerankingError(f"Failed to rerank: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error reranking: {e}")
            raise RerankingError(f"Failed to rerank: {e}") from e

    async def close(self) -> None:
        """Close HTTP client connection."""
        await self.client.aclose()
        logger.debug("OpenVINO client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
