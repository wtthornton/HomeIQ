"""
Database Models for v2 Conversation System

New models for the conversation-based automation system.
These models represent the v2 schema tables.

Created: Phase 1 - Architecture & Database Design
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base

# Use the same Base as existing models
# This ensures all models are in the same metadata
try:
    from .models import Base
except ImportError:
    # Fallback if models not imported yet
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()


class Conversation(Base):
    """Core conversation tracking"""
    __tablename__ = "conversations"

    conversation_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    conversation_type = Column(String, nullable=False)  # 'automation', 'clarification', 'action', 'information'
    status = Column(String, nullable=False, default="active")  # 'active', 'completed', 'abandoned'
    initial_query = Column(Text, nullable=False)
    context = Column(JSON, nullable=True)
    conversation_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Conversation(conversation_id={self.conversation_id}, type={self.conversation_type}, status={self.status})>"


class ConversationTurn(Base):
    """Individual conversation turns"""
    __tablename__ = "conversation_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    turn_number = Column(Integer, nullable=False)
    role = Column(String, nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    response_type = Column(String, nullable=True)  # 'automation_generated', 'clarification_needed', etc.
    intent = Column(String, nullable=True)
    extracted_entities = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_conversation_turns_conversation", "conversation_id", "turn_number"),
    )

    def __repr__(self):
        return f"<ConversationTurn(id={self.id}, conversation_id={self.conversation_id}, turn_number={self.turn_number})>"


class ConfidenceFactor(Base):
    """Enhanced confidence tracking"""
    __tablename__ = "confidence_factors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    turn_id = Column(Integer, nullable=False)
    factor_name = Column(String, nullable=False)  # 'entity_match', 'ambiguity_penalty', etc.
    factor_score = Column(Float, nullable=False)
    factor_weight = Column(Float, nullable=False)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_confidence_conversation", "conversation_id", "turn_id"),
    )


class FunctionCall(Base):
    """Function call tracking"""
    __tablename__ = "function_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    turn_id = Column(Integer, nullable=False)
    function_name = Column(String, nullable=False)
    parameters = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_function_calls_conversation", "conversation_id", "created_at"),
    )


class AutomationSuggestionV2(Base):
    """Enhanced automation suggestions"""
    __tablename__ = "automation_suggestions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    suggestion_id = Column(String, unique=True, nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    turn_id = Column(Integer, nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    automation_yaml = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False)
    response_type = Column(String, nullable=False)
    validated_entities = Column(JSON, nullable=True)
    test_results = Column(JSON, nullable=True)
    status = Column(String, default="draft")  # 'draft', 'tested', 'approved', 'deployed', 'rejected'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_suggestions_conversation", "conversation_id"),
        Index("idx_suggestions_status", "status", "created_at"),
    )

    def __repr__(self):
        return f"<AutomationSuggestionV2(suggestion_id={self.suggestion_id}, status={self.status})>"

