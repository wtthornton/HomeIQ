"""add device intelligence fields

Revision ID: 006
Revises: 005
Create Date: 2025-01-20

Phase 1.1: Add device intelligence fields for Device Database enhancements
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: str | None = "005"
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
    """Add device intelligence fields to devices table"""

    # Add device classification fields
    _add_column_if_missing("devices", sa.Column("device_type", sa.String(), nullable=True))
    _add_column_if_missing("devices", sa.Column("device_category", sa.String(), nullable=True))

    # Add power consumption fields
    _add_column_if_missing(
        "devices", sa.Column("power_consumption_idle_w", sa.Float(), nullable=True)
    )
    _add_column_if_missing(
        "devices", sa.Column("power_consumption_active_w", sa.Float(), nullable=True)
    )
    _add_column_if_missing(
        "devices", sa.Column("power_consumption_max_w", sa.Float(), nullable=True)
    )

    # Add Device Database fields
    _add_column_if_missing("devices", sa.Column("infrared_codes_json", sa.Text(), nullable=True))
    _add_column_if_missing(
        "devices", sa.Column("setup_instructions_url", sa.String(), nullable=True)
    )
    _add_column_if_missing("devices", sa.Column("troubleshooting_notes", sa.Text(), nullable=True))
    _add_column_if_missing("devices", sa.Column("device_features_json", sa.Text(), nullable=True))
    _add_column_if_missing("devices", sa.Column("community_rating", sa.Float(), nullable=True))
    _add_column_if_missing(
        "devices", sa.Column("last_capability_sync", sa.DateTime(), nullable=True)
    )

    # Create indexes for filtering
    _create_index_if_missing("idx_device_type", "devices", ["device_type"])
    _create_index_if_missing("idx_device_category", "devices", ["device_category"])


def downgrade() -> None:
    """Remove device intelligence fields and indexes"""

    # Remove indexes
    op.drop_index("idx_device_category", "devices")
    op.drop_index("idx_device_type", "devices")

    # Remove columns
    _drop_column_if_present("devices", "last_capability_sync")
    _drop_column_if_present("devices", "community_rating")
    _drop_column_if_present("devices", "device_features_json")
    _drop_column_if_present("devices", "troubleshooting_notes")
    _drop_column_if_present("devices", "setup_instructions_url")
    _drop_column_if_present("devices", "infrared_codes_json")
    _drop_column_if_present("devices", "power_consumption_max_w")
    _drop_column_if_present("devices", "power_consumption_active_w")
    _drop_column_if_present("devices", "power_consumption_idle_w")
    _drop_column_if_present("devices", "device_category")
    _drop_column_if_present("devices", "device_type")
