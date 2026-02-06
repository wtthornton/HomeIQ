"""
Database Models for RAG Service

RAGKnowledge model for storing semantic knowledge with embeddings.
Following 2025 patterns: SQLAlchemy async with type hints.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Float, Index, Integer, JSON, String, Text
from sqlalchemy.sql import func

from .session import Base


class RAGKnowledge(Base):
    """
    Semantic knowledge storage for RAG (Retrieval-Augmented Generation).
    
    Stores text with embeddings for semantic similarity search.
    Used for:
    - Query clarification (learn from successful queries)
    - Pattern matching enhancement
    - Suggestion generation
    - Device intelligence
    - Automation mining
    """
    __tablename__ = 'rag_knowledge'

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)  # Original text (query, pattern, blueprint, etc.)
    embedding = Column(JSON, nullable=False)  # 1024-dim BGE-M3-base embedding array (stored as JSON)
    knowledge_type = Column(String, nullable=False)  # 'query', 'pattern', 'blueprint', 'automation', etc.
    metadata_json = Column("metadata", JSON, nullable=True)  # Flexible metadata (device_id, area_id, confidence, etc.) - mapped to 'metadata' column
    success_score = Column(Float, default=0.5, nullable=False)  # 0.0-1.0 (learned from user feedback)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_knowledge_type', 'knowledge_type'),  # Fast filtering by type
        Index('idx_success_score', 'success_score'),  # For ranking by success
        Index('idx_created_at', 'created_at'),  # For time-based queries
    )

    def __repr__(self) -> str:
        return (
            f"<RAGKnowledge(id={self.id}, type='{self.knowledge_type}', "
            f"text='{self.text[:50]}...', success={self.success_score})>"
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            'id': self.id,
            'text': self.text,
            'knowledge_type': self.knowledge_type,
            'metadata': self.metadata_json,  # Use metadata_json attribute, expose as 'metadata' in dict
            'success_score': self.success_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
