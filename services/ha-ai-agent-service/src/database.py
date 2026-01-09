"""Database initialization and models for context cache"""

import logging
import os
import stat
from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, JSON, text
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
            
            # Fix directory permissions if needed (Docker/non-root user)
            # This is critical for Docker volumes which are created as root-owned
            if db_path.parent.exists():
                try:
                    # Get current user ID
                    current_uid = os.getuid() if hasattr(os, 'getuid') else None
                    current_gid = os.getgid() if hasattr(os, 'getgid') else None
                    
                    # Make directory writable for owner and group
                    os.chmod(db_path.parent, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
                    
                    # Try to change ownership if we're not root (in Docker, we're appuser)
                    # Note: This will fail if we don't have permission, but that's OK - chmod should be enough
                    if current_uid is not None and current_uid != 0:
                        try:
                            os.chown(db_path.parent, current_uid, current_gid)
                        except (PermissionError, OSError):
                            # Can't change ownership, but chmod should still work
                            pass
                    
                    logger.info(f"✅ Set directory permissions for {db_path.parent} (UID: {current_uid}, GID: {current_gid})")
                except Exception as perm_error:
                    logger.error(f"❌ Could not set directory permissions: {perm_error}", exc_info=True)
                    # Don't fail initialization - try to continue
            
            # Check database file permissions if it exists
            if db_path.exists():
                # Fix database file permissions if read-only
                try:
                    current_uid = os.getuid() if hasattr(os, 'getuid') else None
                    current_gid = os.getgid() if hasattr(os, 'getgid') else None
                    
                    # Make file readable and writable for owner and group
                    os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH)
                    
                    # Try to change ownership if we're not root
                    if current_uid is not None and current_uid != 0:
                        try:
                            os.chown(db_path, current_uid, current_gid)
                        except (PermissionError, OSError):
                            # Can't change ownership, but chmod should still work
                            pass
                    
                    logger.info(f"✅ Set database file permissions for {db_path} (UID: {current_uid}, GID: {current_gid})")
                except Exception as perm_error:
                    logger.error(f"❌ Could not set database file permissions: {perm_error}", exc_info=True)
                    # Don't fail initialization - try to continue
            
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
        
        # Migrate: Add pending_preview and debug_id columns if they don't exist
        # This handles existing databases that were created before these columns were added
        # Run migration in separate transaction to ensure it commits
        if database_url.startswith("sqlite"):
            try:
                logger.info("🔄 Checking for database migrations...")
                async with _engine.begin() as conn:
                    # Check if table exists first
                    table_result = await conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
                    )
                    table_row = table_result.fetchone()
                    table_exists = table_row is not None
                    
                    if table_exists:
                        # Check and migrate pending_preview column
                        column_result = await conn.execute(
                            text("SELECT COUNT(*) FROM pragma_table_info('conversations') WHERE name = 'pending_preview'")
                        )
                        column_count = column_result.scalar() or 0
                        if column_count == 0:
                            logger.info("🔄 Adding missing column: pending_preview to conversations table")
                            await conn.execute(
                                text("ALTER TABLE conversations ADD COLUMN pending_preview JSON")
                            )
                            logger.info("✅ Successfully added pending_preview column")
                        else:
                            logger.debug("✅ Column pending_preview already exists")
                        
                        # Check and migrate debug_id column
                        debug_id_result = await conn.execute(
                            text("SELECT COUNT(*) FROM pragma_table_info('conversations') WHERE name = 'debug_id'")
                        )
                        debug_id_count = debug_id_result.scalar() or 0
                        if debug_id_count == 0:
                            logger.info("🔄 Adding missing column: debug_id to conversations table")
                            await conn.execute(
                                text("ALTER TABLE conversations ADD COLUMN debug_id TEXT")
                            )
                            logger.info("✅ Successfully added debug_id column")
                            
                            # Generate debug_ids for existing conversations that don't have one
                            from uuid import uuid4
                            logger.info("🔄 Generating debug_ids for existing conversations...")
                            result = await conn.execute(
                                text("SELECT conversation_id FROM conversations WHERE debug_id IS NULL")
                            )
                            rows = result.fetchall()
                            for row in rows:
                                conv_id = row[0]
                                debug_id = str(uuid4())
                                await conn.execute(
                                    text("UPDATE conversations SET debug_id = :debug_id WHERE conversation_id = :conv_id"),
                                    {"debug_id": debug_id, "conv_id": conv_id}
                                )
                            logger.info(f"✅ Generated debug_ids for {len(rows)} existing conversations")
                            
                            # Create index on debug_id
                            try:
                                await conn.execute(
                                    text("CREATE UNIQUE INDEX idx_conversations_debug_id ON conversations(debug_id)")
                                )
                                logger.info("✅ Created index on debug_id column")
                            except Exception as idx_error:
                                logger.warning(f"⚠️  Could not create index on debug_id (may already exist): {idx_error}")
                        else:
                            logger.debug("✅ Column debug_id already exists")
                        
                        # Check and migrate title column (Epic AI-20.9)
                        title_result = await conn.execute(
                            text("SELECT COUNT(*) FROM pragma_table_info('conversations') WHERE name = 'title'")
                        )
                        title_count = title_result.scalar() or 0
                        if title_count == 0:
                            logger.info("🔄 Adding missing column: title to conversations table")
                            await conn.execute(
                                text("ALTER TABLE conversations ADD COLUMN title TEXT")
                            )
                            logger.info("✅ Successfully added title column")
                        else:
                            logger.debug("✅ Column title already exists")
                        
                        # Check and migrate source column (Epic AI-20.9)
                        source_result = await conn.execute(
                            text("SELECT COUNT(*) FROM pragma_table_info('conversations') WHERE name = 'source'")
                        )
                        source_count = source_result.scalar() or 0
                        if source_count == 0:
                            logger.info("🔄 Adding missing column: source to conversations table")
                            await conn.execute(
                                text("ALTER TABLE conversations ADD COLUMN source TEXT DEFAULT 'user'")
                            )
                            logger.info("✅ Successfully added source column")
                            
                            # Create index on source
                            try:
                                await conn.execute(
                                    text("CREATE INDEX idx_conversations_source ON conversations(source)")
                                )
                                logger.info("✅ Created index on source column")
                            except Exception as idx_error:
                                logger.warning(f"⚠️  Could not create index on source (may already exist): {idx_error}")
                        else:
                            logger.debug("✅ Column source already exists")
                    else:
                        logger.debug("ℹ️  Conversations table doesn't exist yet (will be created with all columns)")
            except Exception as e:
                # Log error but don't fail initialization - migration is optional
                logger.warning(f"⚠️  Migration check failed (non-fatal): {e}")
                import traceback
                logger.debug(traceback.format_exc())

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

