"""
Generic RAG (Retrieval-Augmented Generation) Service

Provides semantic knowledge storage and retrieval using embeddings.
Can be used for:
- Query clarification (primary use case)
- Pattern matching enhancement
- Suggestion generation
- Device intelligence
- Automation mining
"""

from .client import RAGClient
from .exceptions import EmbeddingGenerationError, RAGError, RetrievalError, StorageError
from .models import SemanticKnowledge

__all__ = [
    "EmbeddingGenerationError",
    "RAGClient",
    "RAGError",
    "RetrievalError",
    "SemanticKnowledge",
    "StorageError",
]

