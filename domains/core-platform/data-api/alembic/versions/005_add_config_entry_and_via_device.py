"""add config_entry_id and via_device

Revision ID: 005
Revises: 004
Create Date: 2025-01-20

Enhanced Entity Registry: Add config_entry_id to entities and devices, add via_device to devices
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: str | None = "004"
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
    """Add config_entry_id to entities and devices, add via_device to devices"""

    # Add config_entry_id to entities
    _add_column_if_missing("entities", sa.Column("config_entry_id", sa.String(), nullable=True))
    _create_index_if_missing("idx_entity_config_entry", "entities", ["config_entry_id"])

    # Add config_entry_id to devices
    _add_column_if_missing("devices", sa.Column("config_entry_id", sa.String(), nullable=True))
    _create_index_if_missing("idx_device_config_entry", "devices", ["config_entry_id"])

    # Add via_device to devices (self-referential foreign key)
    _add_column_if_missing("devices", sa.Column("via_device", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_devices_via_device", "devices", "devices", ["via_device"], ["device_id"]
    )
    _create_index_if_missing("idx_device_via_device", "devices", ["via_device"])


def downgrade() -> None:
    """Remove added columns and indexes"""

    # Remove indexes and columns from devices
    op.drop_index("idx_device_via_device", "devices")
    op.drop_constraint("fk_devices_via_device", "devices", type_="foreignkey")
    _drop_column_if_present("devices", "via_device")
    op.drop_index("idx_device_config_entry", "devices")
    _drop_column_if_present("devices", "config_entry_id")

    # Remove indexes and columns from entities
    op.drop_index("idx_entity_config_entry", "entities")
    _drop_column_if_present("entities", "config_entry_id")
