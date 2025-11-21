"""Add enable_answer_caching to system_settings

Revision ID: 20250125_enable_answer_caching
Revises: 20250120_semantic_knowledge
Create Date: 2025-01-25

Epic: Answer Caching Improvements
Purpose: Add user preference to enable/disable answer caching
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250125_enable_answer_caching"
down_revision = "20251120_confidence_improvements"  # Follows after latest migration
branch_labels = None
depends_on = None


def upgrade():
    """
    Add enable_answer_caching column to system_settings table.

    Defaults to True (enabled) to maintain existing behavior.
    """
    op.add_column(
        "system_settings",
        sa.Column("enable_answer_caching", sa.Boolean(), nullable=False, server_default="1"),
    )


def downgrade():
    """Remove enable_answer_caching column from system_settings table"""
    op.drop_column("system_settings", "enable_answer_caching")

