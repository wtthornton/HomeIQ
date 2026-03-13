"""Database initialization and models for context cache"""

import logging
import os
from datetime import datetime

from homeiq_data import DatabaseManager
from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

logger = logging.getLogger(__name__)

# PostgreSQL configuration
_schema = os.getenv("DATABASE_SCHEMA", "agent")


class Base(DeclarativeBase):
    """Base class for database models"""
    pass


class ContextCache(Base):
    """Context cache table for storing cached context components"""

    __tablename__ = "context_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    cache_value: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<ContextCache(key={self.cache_key}, expires_at={self.expires_at})>"


class ConversationModel(Base):
    """Conversation table for storing conversations"""

    __tablename__ = "conversations"

    conversation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    state: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )

    # Unique troubleshooting ID for debug screen (stored in DB)
    debug_id: Mapped[str | None] = mapped_column(String(36), unique=True, index=True, nullable=True)

    # Conversation title - auto-generated from first message or user-set
    # Epic AI-20.9: Better conversation naming
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Source of conversation creation
    # Values: 'user' (direct chat), 'proactive' (from proactive suggestions), 'pattern' (from pattern-based)
    # Epic AI-20.9: Track conversation origin
    source: Mapped[str | None] = mapped_column(String(20), default="user", nullable=True, index=True)

    # Relationship to messages
    messages: Mapped[list["MessageModel"]] = relationship(
        "MessageModel",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="MessageModel.created_at",
    )

    # Pending automation preview (2025 Preview-and-Approval Workflow)
    pending_preview: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<ConversationModel(id={self.conversation_id}, state={self.state}, title={self.title})>"


class MessageModel(Base):
    """Message table for storing conversation messages"""

    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text)
    tool_calls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    # Relationship to conversation
    conversation: Mapped["ConversationModel"] = relationship(
        "ConversationModel", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<MessageModel(id={self.message_id}, role={self.role})>"


# Indexes for performance
Index("idx_conversations_created_at", ConversationModel.created_at)
Index("idx_conversations_updated_at", ConversationModel.updated_at)
Index("idx_messages_conversation_id", MessageModel.conversation_id)
Index("idx_messages_created_at", MessageModel.created_at)


# Standardized database manager (lazy initialization)
db = DatabaseManager(
    schema=_schema,
    service_name="ha-ai-agent-service",
    auto_commit_sessions=False,
)

# Module-level aliases for backwards compatibility
engine = None
_session_factory = None


async def init_database(_database_url: str = "") -> bool:
    """
    Initialize database connection and create tables.

    Returns True if successful, False if degraded. Never raises.

    Args:
        _database_url: Unused (kept for API compat). URL resolved from env vars.
    """
    global engine, _session_factory
    result = await db.initialize(base=Base)
    engine = db.engine
    _session_factory = db.session_maker
    return result


async def get_session():
    """Get database session (async generator)."""
    async with db.get_db() as session:
        yield session


async def close_database() -> None:
    """Close database connections."""
    await db.close()
