"""Create memory schema and tables.

Revision ID: 001_create_memory_schema
Revises: None
Create Date: 2026-03-06

"""

from typing import Sequence, Union

from alembic import op


revision: str = "001_create_memory_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create memory schema with tables and indexes."""
    # Create schema
    op.execute("CREATE SCHEMA IF NOT EXISTS memory")

    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create memories table
    op.execute("""
        CREATE TABLE memory.memories (
            id BIGSERIAL PRIMARY KEY,
            content VARCHAR(1024) NOT NULL,
            memory_type VARCHAR(20) NOT NULL,
            confidence FLOAT NOT NULL DEFAULT 0.5,
            source_channel VARCHAR(20) NOT NULL,
            source_service VARCHAR(50),
            entity_ids TEXT[],
            area_ids TEXT[],
            tags TEXT[],
            embedding vector(768),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_accessed TIMESTAMPTZ,
            access_count INTEGER DEFAULT 0,
            superseded_by BIGINT REFERENCES memory.memories(id),
            metadata JSONB,
            CONSTRAINT chk_memory_type CHECK (
                memory_type IN (
                    'fact',
                    'preference',
                    'pattern',
                    'context',
                    'correction'
                )
            )
        )
    """)

    # Create memory_archive table
    op.execute("""
        CREATE TABLE memory.memory_archive (
            id BIGSERIAL PRIMARY KEY,
            original_id BIGINT NOT NULL,
            content VARCHAR(1024) NOT NULL,
            memory_type VARCHAR(20) NOT NULL,
            confidence FLOAT NOT NULL DEFAULT 0.5,
            source_channel VARCHAR(20) NOT NULL,
            source_service VARCHAR(50),
            entity_ids TEXT[],
            area_ids TEXT[],
            tags TEXT[],
            embedding vector(768),
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            last_accessed TIMESTAMPTZ,
            access_count INTEGER DEFAULT 0,
            superseded_by BIGINT,
            metadata JSONB,
            archived_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            archive_reason VARCHAR(100),
            CONSTRAINT chk_archive_memory_type CHECK (
                memory_type IN (
                    'fact',
                    'preference',
                    'pattern',
                    'context',
                    'correction'
                )
            )
        )
    """)

    # Create FTS index for full-text search on content
    op.execute("""
        CREATE INDEX idx_memories_fts
        ON memory.memories
        USING gin(to_tsvector('english', content))
    """)

    # Create HNSW vector index for similarity search
    op.execute("""
        CREATE INDEX idx_memories_embedding
        ON memory.memories
        USING hnsw (embedding vector_cosine_ops)
    """)

    # Create composite index for type and confidence queries
    op.execute("""
        CREATE INDEX idx_memories_type_conf
        ON memory.memories (memory_type, confidence DESC)
    """)

    # Create GIN index on entity_ids for array containment queries
    op.execute("""
        CREATE INDEX idx_memories_entities
        ON memory.memories
        USING gin(entity_ids)
    """)


def downgrade() -> None:
    """Drop memory schema and all objects."""
    # Drop indexes (implicit when table dropped, but explicit for clarity)
    op.execute("DROP INDEX IF EXISTS memory.idx_memories_entities")
    op.execute("DROP INDEX IF EXISTS memory.idx_memories_type_conf")
    op.execute("DROP INDEX IF EXISTS memory.idx_memories_embedding")
    op.execute("DROP INDEX IF EXISTS memory.idx_memories_fts")

    # Drop tables in reverse order (archive first, then memories)
    op.execute("DROP TABLE IF EXISTS memory.memory_archive")
    op.execute("DROP TABLE IF EXISTS memory.memories")

    # Drop schema
    op.execute("DROP SCHEMA IF EXISTS memory")
