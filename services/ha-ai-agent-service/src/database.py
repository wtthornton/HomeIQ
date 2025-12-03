"""Database initialization and models for context cache"""

import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

logger = logging.getLogger(__name__)


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

    # Relationship to messages
    messages: Mapped[list["MessageModel"]] = relationship(
        "MessageModel",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="MessageModel.created_at",
    )

    def __repr__(self) -> str:
        return f"<ConversationModel(id={self.conversation_id}, state={self.state})>"


class MessageModel(Base):
    """Message table for storing conversation messages"""

    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text)
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


# Global engine and session factory
_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_database(database_url: str) -> None:
    """
    Initialize database connection and create tables.

    Args:
        database_url: SQLite database URL (e.g., "sqlite+aiosqlite:///./data/ha_ai_agent.db")
    """
    global _engine, _session_factory

    try:
        # Create data directory if it doesn't exist
        if database_url.startswith("sqlite"):
            # Extract path from SQLite URL
            path_str = database_url.split("///")[-1]
            db_path = Path(path_str)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Database directory created: {db_path.parent}")

        # Create async engine
        _engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,  # Verify connections before using
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
        )

        # Create session factory
        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        # Create tables
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}", exc_info=True)
        raise


async def get_session():
    """
    Get database session (async generator).

    Yields:
        AsyncSession instance

    Raises:
        RuntimeError: If database not initialized
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    async with _session_factory() as session:
        yield session


async def close_database() -> None:
    """Close database connections"""
    global _engine, _session_factory

    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("✅ Database connections closed")

