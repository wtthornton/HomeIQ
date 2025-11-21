"""
Custom exceptions for RAG service
"""


class RAGError(Exception):
    """Base exception for RAG service errors"""


class EmbeddingGenerationError(RAGError):
    """Error generating embeddings from OpenVINO service"""


class StorageError(RAGError):
    """Error storing semantic knowledge"""


class RetrievalError(RAGError):
    """Error retrieving semantic knowledge"""

