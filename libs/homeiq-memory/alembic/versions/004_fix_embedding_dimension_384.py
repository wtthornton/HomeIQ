"""Fix embedding vector dimension from 768 to 384.

Revision ID: 004_fix_embedding_dimension_384
Revises: 003_add_domain_and_fix_fk
Create Date: 2026-03-16

The default embedding model (all-MiniLM-L6-v2) produces 384-dimensional
vectors, but the column and HNSW index were created with vector(768).
This migration corrects the mismatch to prevent dimension errors on insert.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "004_fix_embedding_dimension_384"
down_revision: str | None = "003_add_domain_and_fix_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Change embedding column from vector(768) to vector(384)."""
    # Drop the HNSW index (cannot ALTER column type with index present)
    op.execute("DROP INDEX IF EXISTS memory.idx_memories_embedding")

    # Alter column type — existing rows with embeddings will be truncated,
    # so clear them first (they need re-generation with the correct model)
    op.execute(
        "UPDATE memory.memories SET embedding = NULL "
        "WHERE embedding IS NOT NULL"
    )
    op.execute(
        "ALTER TABLE memory.memories "
        "ALTER COLUMN embedding TYPE vector(384)"
    )

    # Same for archive table
    op.execute(
        "UPDATE memory.memory_archive SET embedding = NULL "
        "WHERE embedding IS NOT NULL"
    )
    op.execute(
        "ALTER TABLE memory.memory_archive "
        "ALTER COLUMN embedding TYPE vector(384)"
    )

    # Recreate the HNSW index with correct dimensions
    op.execute(
        "CREATE INDEX idx_memories_embedding "
        "ON memory.memories "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    """Revert embedding column from vector(384) to vector(768)."""
    op.execute("DROP INDEX IF EXISTS memory.idx_memories_embedding")

    op.execute(
        "UPDATE memory.memories SET embedding = NULL "
        "WHERE embedding IS NOT NULL"
    )
    op.execute(
        "ALTER TABLE memory.memories "
        "ALTER COLUMN embedding TYPE vector(768)"
    )

    op.execute(
        "UPDATE memory.memory_archive SET embedding = NULL "
        "WHERE embedding IS NOT NULL"
    )
    op.execute(
        "ALTER TABLE memory.memory_archive "
        "ALTER COLUMN embedding TYPE vector(768)"
    )

    op.execute(
        "CREATE INDEX idx_memories_embedding "
        "ON memory.memories "
        "USING hnsw (embedding vector_cosine_ops)"
    )
