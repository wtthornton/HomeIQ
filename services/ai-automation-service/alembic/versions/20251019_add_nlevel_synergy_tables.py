"""Add n-level synergy detection tables

Revision ID: 20251019_nlevel
Revises: 20251018_add_synergy_opportunities
Create Date: 2025-10-19 14:30:00.000000

Epic AI-4: N-Level Synergy Detection
Story AI4.1: Device Embedding Generation
"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251019_nlevel"
down_revision = "20251018_synergy"  # Previous migration
branch_labels = None
depends_on = None


def upgrade():
    """
    Add tables and columns for n-level synergy detection.

    New table: device_embeddings
    Updated table: synergy_opportunities (add columns for n-level)
    """

    # Create device_embeddings table
    op.create_table(
        "device_embeddings",
        sa.Column("entity_id", sa.String(), nullable=False, primary_key=True),
        sa.Column("embedding", sa.LargeBinary(), nullable=False,
                  comment="384-dim float32 numpy array (1536 bytes)"),
        sa.Column("descriptor", sa.Text(), nullable=False,
                  comment="Natural language device description"),
        sa.Column("last_updated", sa.DateTime(), nullable=False,
                  default=datetime.utcnow,
                  comment="Last embedding generation timestamp"),
        sa.Column("model_version", sa.String(), nullable=False,
                  default="all-MiniLM-L6-v2-int8",
                  comment="Embedding model version"),
        sa.Column("embedding_norm", sa.Float(), nullable=True,
                  comment="L2 norm for validation (should be ~1.0 if normalized)"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.entity_id"],
                               ondelete="CASCADE"),
        comment="Device semantic embeddings for n-level synergy detection",
    )

    # Create indexes on device_embeddings
    op.create_index(
        "idx_device_embeddings_updated",
        "device_embeddings",
        ["last_updated"],
    )
    op.create_index(
        "idx_device_embeddings_version",
        "device_embeddings",
        ["model_version"],
    )

    # Add columns to synergy_opportunities for n-level support
    with op.batch_alter_table("synergy_opportunities") as batch_op:
        # Chain depth (2 = existing 2-level, 3+ = n-level)
        batch_op.add_column(
            sa.Column("synergy_depth", sa.Integer(), nullable=False,
                     server_default="2",
                     comment="Number of devices in chain (2 = pair, 3+ = multi-hop)"),
        )

        # JSON array of entity_ids in chain
        batch_op.add_column(
            sa.Column("chain_devices", sa.Text(), nullable=True,
                     comment="JSON array of entity_ids in automation chain"),
        )

        # Embedding similarity score (from Phase 2)
        batch_op.add_column(
            sa.Column("embedding_similarity", sa.Float(), nullable=True,
                     comment="Semantic similarity score from embeddings"),
        )

        # Re-ranker score (from Phase 3)
        batch_op.add_column(
            sa.Column("rerank_score", sa.Float(), nullable=True,
                     comment="Cross-encoder re-ranking score"),
        )

        # Final combined score
        batch_op.add_column(
            sa.Column("final_score", sa.Float(), nullable=True,
                     comment="Combined score (0.5*embedding + 0.5*rerank)"),
        )

        # Complexity assessment
        batch_op.add_column(
            sa.Column("complexity", sa.String(20), nullable=True,
                     comment="easy, medium, or advanced"),
        )

    # Create indexes on synergy_opportunities for n-level queries
    op.create_index(
        "idx_synergy_depth",
        "synergy_opportunities",
        ["synergy_depth"],
    )
    op.create_index(
        "idx_synergy_final_score",
        "synergy_opportunities",
        ["final_score"],
        postgresql_ops={"final_score": "DESC"},
    )
    op.create_index(
        "idx_synergy_complexity",
        "synergy_opportunities",
        ["complexity"],
    )


def downgrade():
    """
    Remove n-level synergy detection tables and columns.
    """

    # Drop indexes on synergy_opportunities
    op.drop_index("idx_synergy_complexity", "synergy_opportunities")
    op.drop_index("idx_synergy_final_score", "synergy_opportunities")
    op.drop_index("idx_synergy_depth", "synergy_opportunities")

    # Remove columns from synergy_opportunities
    with op.batch_alter_table("synergy_opportunities") as batch_op:
        batch_op.drop_column("complexity")
        batch_op.drop_column("final_score")
        batch_op.drop_column("rerank_score")
        batch_op.drop_column("embedding_similarity")
        batch_op.drop_column("chain_devices")
        batch_op.drop_column("synergy_depth")

    # Drop indexes on device_embeddings
    op.drop_index("idx_device_embeddings_version", "device_embeddings")
    op.drop_index("idx_device_embeddings_updated", "device_embeddings")

    # Drop device_embeddings table
    op.drop_table("device_embeddings")

