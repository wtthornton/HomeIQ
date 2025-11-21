"""Initial schema for community automations

Revision ID: 001
Revises:
Create Date: 2025-10-18 20:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create community_automations table
    op.create_table(
        "community_automations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("source_id", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("devices", sa.JSON(), nullable=False),
        sa.Column("integrations", sa.JSON(), nullable=False),
        sa.Column("triggers", sa.JSON(), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("use_case", sa.String(length=20), nullable=False),
        sa.Column("complexity", sa.String(length=10), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("vote_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_crawled", sa.DateTime(), nullable=False),
        sa.Column("extra_metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "source_id", name="uq_source_source_id"),
    )

    # Create indexes
    op.create_index("ix_source", "community_automations", ["source"])
    op.create_index("ix_use_case", "community_automations", ["use_case"])
    op.create_index("ix_quality_score", "community_automations", ["quality_score"])

    # Create miner_state table
    op.create_table(
        "miner_state",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("miner_state")
    op.drop_index("ix_quality_score", "community_automations")
    op.drop_index("ix_use_case", "community_automations")
    op.drop_index("ix_source", "community_automations")
    op.drop_table("community_automations")

