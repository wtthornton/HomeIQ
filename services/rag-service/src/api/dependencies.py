"""
Dependency Injection Helpers (2025 Patterns)

Following 2025 FastAPI dependency injection patterns with Annotated types.
"""

import logging
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.openvino_client import OpenVINOClient
from ..config import settings
from ..database.session import get_db
from ..services.rag_service import RAGService

logger = logging.getLogger(__name__)

# Type aliases for cleaner dependency injection (2025 pattern)
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


def get_openvino_client() -> OpenVINOClient:
    """Get OpenVINO client instance."""
    return OpenVINOClient(base_url=settings.openvino_service_url)


def get_rag_service(
    db: DatabaseSession,
    openvino_client: Annotated[OpenVINOClient, Depends(get_openvino_client)]
) -> RAGService:
    """Get RAG service instance."""
    return RAGService(
        db=db,
        openvino_client=openvino_client,
        embedding_cache_size=settings.embedding_cache_size
    )


# Type alias for RAG service dependency
RAGServiceDep = Annotated[RAGService, Depends(get_rag_service)]
