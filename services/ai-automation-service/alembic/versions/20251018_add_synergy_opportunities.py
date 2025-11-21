"""Add synergy_opportunities table for Epic AI-3

Revision ID: 20251018_synergy
Revises: 20251016_095206_add_device_intelligence_tables
Create Date: 2025-10-18

Story AI3.1: Device Synergy Detector Foundation
Epic AI-3: Cross-Device Synergy & Contextual Opportunities
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251018_synergy"
down_revision = "004"  # Latest revision (conversational fields)
branch_labels = None
depends_on = None


def upgrade():
    """
    Create synergy_opportunities table.

    Stores cross-device synergy opportunities detected by DeviceSynergyDetector.
    """
    op.create_table(
        "synergy_opportunities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("synergy_id", sa.String(36), nullable=False),
        sa.Column("synergy_type", sa.String(50), nullable=False),
        sa.Column("device_ids", sa.Text(), nullable=False),
        sa.Column("opportunity_metadata", sa.JSON(), nullable=True),
        sa.Column("impact_score", sa.Float(), nullable=False),
        sa.Column("complexity", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("area", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for fast lookups
    op.create_index("ix_synergy_opportunities_synergy_id", "synergy_opportunities", ["synergy_id"], unique=True)
    op.create_index("ix_synergy_opportunities_synergy_type", "synergy_opportunities", ["synergy_type"], unique=False)


def downgrade():
    """Drop synergy_opportunities table and indexes."""
    op.drop_index("ix_synergy_opportunities_synergy_type", table_name="synergy_opportunities")
    op.drop_index("ix_synergy_opportunities_synergy_id", table_name="synergy_opportunities")
    op.drop_table("synergy_opportunities")

