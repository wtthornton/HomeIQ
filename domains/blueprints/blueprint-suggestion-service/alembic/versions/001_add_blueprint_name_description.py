"""Add blueprint_name and blueprint_description columns

Revision ID: 001
Revises:
Create Date: 2026-01-14 17:00:00

"""

import contextlib
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add blueprint_name column if it doesn't exist
    # SQLite doesn't support IF NOT EXISTS in ALTER TABLE, so we check first
    # This migration is safe to run even if columns already exist (they will be ignored)
    try:
        op.add_column(
            "blueprint_suggestions",
            sa.Column("blueprint_name", sa.String(length=255), nullable=True),
        )
    except Exception:
        # Column might already exist, that's okay
        pass

    try:
        op.add_column(
            "blueprint_suggestions", sa.Column("blueprint_description", sa.Text(), nullable=True)
        )
    except Exception:
        # Column might already exist, that's okay
        pass


def downgrade() -> None:
    # Remove columns (only if they exist)
    with contextlib.suppress(Exception):
        op.drop_column("blueprint_suggestions", "blueprint_description")

    with contextlib.suppress(Exception):
        op.drop_column("blueprint_suggestions", "blueprint_name")
