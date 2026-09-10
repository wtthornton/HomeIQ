"""
OpenVINO Model Bridge

TAP-7276: RAG used to reach a separate openvino-service container over HTTP
for embeddings/reranking. In the merged model-server process there is only
one ``OpenVINOManager`` -- the same instance the ``/embeddings`` and
``/rerank`` routes use -- so ``LocalOpenVINOBridge`` delegates to it
in-process instead of loading a second copy of the model or round-tripping
over the network to a container that no longer exists.
"""

import logging
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ...openvino.models.openvino_manager import OpenVINOManager


class OpenVINOClientError(Exception):
    """Base exception for OpenVINO bridge errors."""

    pass


class EmbeddingGenerationError(OpenVINOClientError):
    """Exception raised when embedding generation fails."""

    pass


class RerankingError(OpenVINOClientError):
    """Exception raised when reranking fails."""

    pass


class LocalOpenVINOBridge:
    """In-process adapter around the shared ``OpenVINOManager``.

    Keeps the same public surface RAG's dependency-injection code already
    expects (``get_embeddings``, ``rerank``, ``is_ready``) so
    ``rag_service.py`` and ``dependencies.py`` need no changes.
    """

    def __init__(self, manager: "OpenVINOManager") -> None:
        self._manager = manager

    async def get_embeddings(self, texts: list[str], normalize: bool = True) -> list[list[float]]:
        """Get embeddings for texts from the shared OpenVINO manager."""
        if not texts:
            return []
        embeddings = await self._manager.generate_embeddings(texts=texts, normalize=normalize)
        return embeddings.tolist()

    async def rerank(self, query: str, candidates: list[dict[str, Any]], top_k: int = 10) -> list[dict[str, Any]]:
        """Rerank candidates using the shared OpenVINO manager."""
        if not candidates:
            return []
        return await self._manager.rerank(query=query, candidates=candidates, top_k=top_k)

    def is_ready(self) -> bool:
        return self._manager.is_ready()

    async def close(self) -> None:
        """No-op: lifecycle is owned by the shared manager's own shutdown hook."""
        return None
