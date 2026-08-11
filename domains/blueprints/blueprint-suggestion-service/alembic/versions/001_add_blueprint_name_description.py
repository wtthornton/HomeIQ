"""Add blueprint_name and blueprint_description columns

Revision ID: 001
Revises:
Create Date: 2026-01-14 17:00:00

Both columns are already present in infrastructure/postgres/init-schemas.sql,
which owns the base shape of blueprints.blueprint_suggestions. This migration
therefore only does work on databases created before those columns were added
there, and must be a no-op everywhere else.

It used to express that by wrapping each add_column in `except Exception: pass`.
That does not work on PostgreSQL: a failed statement aborts the surrounding
transaction, so swallowing the error left the connection unusable and the very
next statement died with InFailedSQLTransactionError. The migration reported
success while doing nothing, and `alembic upgrade head` failed outright on a
fresh database. Ask the catalog instead of guessing from an exception.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "blueprint_suggestions"


def _columns() -> set[str]:
    """Names of the columns currently on TABLE, resolved via search_path."""
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(TABLE)}


def upgrade() -> None:
    existing = _columns()

    if "blueprint_name" not in existing:
        op.add_column(TABLE, sa.Column("blueprint_name", sa.String(length=255), nullable=True))

    if "blueprint_description" not in existing:
        op.add_column(TABLE, sa.Column("blueprint_description", sa.Text(), nullable=True))


def downgrade() -> None:
    existing = _columns()

    if "blueprint_description" in existing:
        op.drop_column(TABLE, "blueprint_description")

    if "blueprint_name" in existing:
        op.drop_column(TABLE, "blueprint_name")
