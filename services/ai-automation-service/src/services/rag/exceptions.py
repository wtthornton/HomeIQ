"""
Custom exceptions for RAG service
"""


class RAGError(Exception):
    """Base exception for RAG service errors"""
    pass


class EmbeddingGenerationError(RAGError):
    """Error generating embeddings from OpenVINO service"""
    pass


class StorageError(RAGError):
    """Error storing semantic knowledge"""
    pass


class RetrievalError(RAGError):
    """Error retrieving semantic knowledge"""
    pass

