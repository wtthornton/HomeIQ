"""add missing device columns

Revision ID: 003
Revises: 002
Create Date: 2025-10-31

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _schema() -> str:
    """Schema in effect; an unqualified inspector lookup would resolve to public."""
    return op.get_bind().exec_driver_sql("SELECT current_schema()").scalar()


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(table, schema=_schema())}


def _indexes(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {ix["name"] for ix in inspector.get_indexes(table, schema=_schema()) if ix.get("name")}


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    """init-schemas.sql already defines most of these columns.

    Adding one that exists raises DuplicateColumn, and on PostgreSQL that aborts
    the surrounding transaction, so the failure takes every later statement in
    the migration with it.
    """
    if column.name not in _columns(table):
        op.add_column(table, column)


def _drop_column_if_present(table: str, name: str) -> None:
    if name in _columns(table):
        op.drop_column(table, name)


def _create_index_if_missing(name: str, table: str, columns: list[str], **kw) -> None:
    if name not in _indexes(table):
        op.create_index(name, table, columns, **kw)


def _drop_index_if_present(name: str, table: str) -> None:
    if name in _indexes(table):
        op.drop_index(name, table_name=table)


def upgrade() -> None:
    """Add missing columns to devices table"""

    # Add missing columns to devices table
    _add_column_if_missing("devices", sa.Column("name_by_user", sa.String(), nullable=True))
    _add_column_if_missing("devices", sa.Column("entry_type", sa.String(), nullable=True))
    _add_column_if_missing("devices", sa.Column("configuration_url", sa.String(), nullable=True))
    _add_column_if_missing("devices", sa.Column("suggested_area", sa.String(), nullable=True))


def downgrade() -> None:
    """Remove added columns from devices table"""

    # Remove columns in reverse order
    _drop_column_if_present("devices", "suggested_area")
    _drop_column_if_present("devices", "configuration_url")
    _drop_column_if_present("devices", "entry_type")
    _drop_column_if_present("devices", "name_by_user")
